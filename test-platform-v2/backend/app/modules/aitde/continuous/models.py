"""AITDE V3.5 Continuous Acceptance models (V35).

Data model for Environment Fingerprint → Build Observation → Execution Campaign
→ Quality Gate (plan §2). Created by the M35 alembic migration. String-valued
enums so they stay stable across SQLite/PostgreSQL.
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
from app.modules.aitde.common.enums import (
    BuildObservationStatus,
    CampaignScenarioRequired,
    CampaignType,
    ContinuousTriggerType,
    FingerprintSourceType,
    QualityGateResult,
)


class EnvironmentFingerprint(Base):
    """V35-001: a stable, deduplicated environment fingerprint (non-secret hash)."""

    __tablename__ = "environment_fingerprints"
    __table_args__ = (
        UniqueConstraint("environment_id", "fingerprint_hash", name="uq_env_fingerprint_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    environment_id: Mapped[int] = mapped_column(Integer, index=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), index=True)
    build_label: Mapped[str | None] = mapped_column(String(128), default=None)
    components_json: Mapped[str] = mapped_column(Text, default="{}")
    source_type: Mapped[str] = mapped_column(
        String(16), default=FingerprintSourceType.AUTO.value, index=True
    )
    # V3.9-R3 (FINGER-001): how confident we are this fingerprint was OBSERVED
    # (probed) vs manually declared. A P0 release gate requires MEDIUM/HIGH.
    confidence: Mapped[str] = mapped_column(String(16), default="LOW", index=True)
    captured_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class BuildObservation(Base):
    """V35-002: a detected environment change (deduplicated by fingerprint)."""

    __tablename__ = "build_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    environment_id: Mapped[int] = mapped_column(Integer, index=True)
    fingerprint_id: Mapped[int] = mapped_column(Integer, index=True)
    previous_fingerprint_id: Mapped[int | None] = mapped_column(Integer, default=None)
    change_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    detected_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
    status: Mapped[str] = mapped_column(
        String(16), default=BuildObservationStatus.NEW.value, index=True
    )


class ExecutionCampaign(Base):
    """V35-003: a fixed selection snapshot for one Build."""

    __tablename__ = "execution_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    campaign_type: Mapped[str] = mapped_column(
        String(32), default=CampaignType.IMPACTED.value, index=True
    )
    environment_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    build_observation_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    created_by_type: Mapped[str] = mapped_column(String(16), default="AUTO")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class RunProfile(Base):
    """V35-004: a reusable run profile (smoke/full/custom)."""

    __tablename__ = "run_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    selector_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_policy_json: Mapped[str] = mapped_column(Text, default="{}")
    retry_policy_json: Mapped[str] = mapped_column(Text, default="{}")
    parallelism: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)


class CampaignScenario(Base):
    """V35-003: a scenario selected into a campaign (immutable after run start)."""

    __tablename__ = "campaign_scenarios"
    __table_args__ = (
        UniqueConstraint("campaign_id", "scenario_version_id", name="uq_campaign_scenario"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    selection_reason_json: Mapped[str] = mapped_column(Text, default="{}")
    required: Mapped[str] = mapped_column(
        String(16), default=CampaignScenarioRequired.REQUIRED.value, index=True
    )
    run_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)


class Trigger(Base):
    """V35-008: a re-runnable trigger (manual/schedule/fingerprint/webhook)."""

    __tablename__ = "triggers"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    trigger_type: Mapped[str] = mapped_column(
        String(16), default=ContinuousTriggerType.MANUAL.value, index=True
    )
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class QualityGatePolicy(Base):
    """V35-007: a versioned Quality Gate policy (G1-G10)."""

    __tablename__ = "quality_gate_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    policy_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class QualityGateResultRecord(Base):
    """V35-007: the evaluated Quality Gate result for one Build (append-only)."""

    __tablename__ = "quality_gate_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    campaign_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    build_observation_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    policy_id: Mapped[int] = mapped_column(Integer, index=True)
    result: Mapped[str] = mapped_column(
        String(16), default=QualityGateResult.INCONCLUSIVE.value, index=True
    )
    checks_json: Mapped[str] = mapped_column(Text, default="[]")
    evaluated_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
    override_status: Mapped[str | None] = mapped_column(String(16), default=None)
    override_by: Mapped[int | None] = mapped_column(Integer, default=None)
    override_reason: Mapped[str | None] = mapped_column(Text, default=None)
