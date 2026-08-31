"""AITDE V3.1 execution models (V31).

Unified Execution + Proof Replay data model: binds ``scenario_version_id`` +
``contract_version_id`` + ``environment_snapshot_id`` for every run, keeps
``runtime_status`` (scheduler) separate from ``outcome`` (business conclusion),
and stores artifacts' metadata/hash only (never raw bytes) so the DB stays lean.

These tables are created by migrations M31-1 / M31-2 / M31-3. The environment,
assertion and evidence modules are service/engine layers over these models.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (  # noqa: F401  (re-exported for consumers)
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import (
    AdapterStatus,
    AdapterType,
    AssertionResult,
    AssertionTrustStatus,
    EvidenceIntegrityStatus,
    EvidenceStatus,
    EvidenceType,
    LegacyExecutionType,
    OracleSourceType,
    RunStatus,
    SanitizationStatus,
    StepStatus,
    StepType,
    TriggerType,
)


class ScenarioAdapter(Base, TimestampMixin):
    """M31-1: bind a ScenarioVersion to an existing API/UI asset or future Runtime Adapter."""

    __tablename__ = "scenario_adapters"
    __table_args__ = (
        UniqueConstraint(
            "scenario_version_id", "adapter_type", "adapter_version",
            name="uq_scenario_adapter_version_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    adapter_type: Mapped[str] = mapped_column(
        String(16), default=AdapterType.API.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=AdapterStatus.DRAFT.value, index=True
    )
    source_asset_type: Mapped[str | None] = mapped_column(String(64), default=None)
    source_asset_id: Mapped[int | None] = mapped_column(Integer, default=None)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    adapter_version: Mapped[str] = mapped_column(String(64), default="1.0")
    created_by: Mapped[int] = mapped_column(Integer, default=0)


class EnvironmentSnapshot(Base):
    """M31-1: environment fingerprint captured at run start; every run binds one."""

    __tablename__ = "environment_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    environment_id: Mapped[int] = mapped_column(Integer, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    build_label: Mapped[str | None] = mapped_column(String(128), default=None)
    frontend_version: Mapped[str | None] = mapped_column(String(64), default=None)
    service_versions_json: Mapped[str] = mapped_column(Text, default="{}")
    openapi_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    db_schema_version: Mapped[str | None] = mapped_column(String(64), default=None)
    config_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    static_asset_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    manual_note: Mapped[str | None] = mapped_column(Text, default=None)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    captured_at: Mapped[datetime] = mapped_column(default=datetime.now)
    created_by_type: Mapped[str] = mapped_column(String(16), default="AUTO")
    # V3.9-R3 (FINGER-001): how confident the snapshot was actually observed.
    confidence: Mapped[str] = mapped_column(String(16), default="LOW", index=True)


class ExecutionRun(Base):
    """M31-2: one unified execution unit. runtime_status != outcome."""

    __tablename__ = "execution_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    contract_version_id: Mapped[int] = mapped_column(Integer, index=True)
    adapter_id: Mapped[int | None] = mapped_column(Integer, default=None)
    environment_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    environment_snapshot_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    runtime_status: Mapped[str] = mapped_column(
        String(16), default=RunStatus.QUEUED.value, index=True
    )
    outcome: Mapped[str | None] = mapped_column(String(32), default=None, index=True)
    evidence_status: Mapped[str] = mapped_column(
        String(16), default=EvidenceStatus.PENDING.value, index=True
    )
    trigger_type: Mapped[str] = mapped_column(
        String(16), default=TriggerType.MANUAL.value
    )
    parent_run_id: Mapped[int | None] = mapped_column(Integer, default=None)
    retry_no: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ExecutionStep(Base):
    """M31-2: one step within a run, appended to an ordered timeline."""

    __tablename__ = "execution_steps"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_run_step_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    step_key: Mapped[str] = mapped_column(String(128), default="")
    step_type: Mapped[str] = mapped_column(
        String(16), default=StepType.ACTION.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=StepStatus.PENDING.value, index=True
    )
    error_type: Mapped[str | None] = mapped_column(String(64), default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    input_snapshot_json: Mapped[str | None] = mapped_column(Text, default=None)
    output_snapshot_json: Mapped[str | None] = mapped_column(Text, default=None)
    # V3.9-R1 (TRUST-003): real EvidenceArtifact ids produced by this step.
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    trace_id: Mapped[str | None] = mapped_column(String(128), default=None)
    span_id: Mapped[str | None] = mapped_column(String(128), default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class AssertionResult(Base):
    """M31-2: one Oracle evaluation result. NOT_EVALUATED never counts as PASS."""

    __tablename__ = "assertion_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    step_id: Mapped[int | None] = mapped_column(Integer, default=None)
    oracle_id: Mapped[int] = mapped_column(Integer, index=True)
    # V3.9-R1 (TRUST-001): the real TestOracle id. ``oracle_id`` is retained as
    # legacy-compat; new Runtime writes ``test_oracle_id`` only.
    test_oracle_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    oracle_source_type: Mapped[str] = mapped_column(
        String(32), default=OracleSourceType.LEGACY_EXECUTION.value, index=True
    )
    trust_status: Mapped[str] = mapped_column(
        String(32), default=AssertionTrustStatus.LEGACY_UNVERIFIED.value, index=True
    )
    binding_id: Mapped[int | None] = mapped_column(Integer, default=None)
    oracle_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    expected_json: Mapped[str] = mapped_column(Text, default="{}")
    actual_json: Mapped[str] = mapped_column(Text, default="{}")
    result: Mapped[str] = mapped_column(
        String(16), default=AssertionResult.NOT_EVALUATED.value, index=True
    )
    reason_code: Mapped[str] = mapped_column(String(64), default="")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class EvidenceArtifact(Base):
    """M31-3: artifact metadata + hash; raw bytes live in object storage."""

    __tablename__ = "evidence_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    step_id: Mapped[int | None] = mapped_column(Integer, default=None)
    evidence_type: Mapped[str] = mapped_column(
        String(32), default=EvidenceType.RESPONSE.value, index=True
    )
    storage_provider: Mapped[str] = mapped_column(String(32), default="local")
    storage_uri: Mapped[str] = mapped_column(String(512), default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    content_type: Mapped[str] = mapped_column(String(128), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sanitization_status: Mapped[str] = mapped_column(
        String(16), default=SanitizationStatus.PENDING.value, index=True
    )
    sensitivity: Mapped[str] = mapped_column(String(16), default="normal")
    retention_class: Mapped[str] = mapped_column(String(32), default="standard")
    # V3.9-R1 (TRUST-004): physical integrity of the stored object.
    integrity_status: Mapped[str] = mapped_column(
        String(16), default=EvidenceIntegrityStatus.PENDING.value, index=True
    )
    storage_verified_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    sanitizer_version: Mapped[str | None] = mapped_column(String(32), default=None)
    storage_etag: Mapped[str | None] = mapped_column(String(128), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class ReplayManifest(Base):
    """M31-3: append-only proof replay manifest for a run."""

    __tablename__ = "replay_manifests"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0")
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    manifest_hash: Mapped[str] = mapped_column(String(64), default="")
    generated_at: Mapped[datetime] = mapped_column(default=datetime.now)


class LegacyExecutionLink(Base):
    """M31-3: bridge a unified Run to its legacy API/UI/TestExecution source record."""

    __tablename__ = "legacy_execution_links"
    __table_args__ = (
        UniqueConstraint("legacy_type", "legacy_id", name="uq_legacy_execution_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    legacy_type: Mapped[str] = mapped_column(
        String(32), default=LegacyExecutionType.API_TASK_ITEM.value, index=True
    )
    legacy_id: Mapped[int] = mapped_column(Integer, index=True)


class ShadowAuditFeedback(Base):
    """M31-4: tester deep-audit feedback on a Run's outcome.

    Records CONFIRMED / FALSE_PASS / FALSE_FAIL. Feedback is append-only and
    NEVER mutates the Run's historical ``outcome`` (the audit is a monitoring
    signal, not a verdict override).
    """

    __tablename__ = "shadow_audit_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    audit_outcome: Mapped[str] = mapped_column(String(16), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
