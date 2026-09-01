"""AITDE V4.0 Enterprise governance data models (V40-009..020).

Enterprise tables per the V4.0 plan §3: ``retention_policies`` (V40-012),
``model_policies`` (V40-014), ``model_usage_ledger`` (V40-015),
``governance_exceptions`` (V40-011) and ``dr_test_runs`` (V40-017). Created by
the M40 governance alembic migration. String-valued enums stay stable across
SQLite/PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.governance.enums import (
    ArtifactType,
    DrTestStatus,
    DrTestType,
    GovernanceExceptionStatus,
    PolicyStatus,
    RetentionAction,
    SensitivityLevel,
)


class RetentionPolicy(Base):
    """V40-012: how long an artifact type/sensitivity may be retained."""

    __tablename__ = "retention_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    artifact_type: Mapped[str] = mapped_column(
        String(16), default=ArtifactType.EVIDENCE.value, index=True
    )
    sensitivity: Mapped[str] = mapped_column(
        String(16), default=SensitivityLevel.INTERNAL.value, index=True
    )
    retention_days: Mapped[int] = mapped_column(Integer, default=90)
    archive_action: Mapped[str] = mapped_column(
        String(16), default=RetentionAction.ARCHIVE.value
    )
    delete_action: Mapped[str] = mapped_column(
        String(16), default=RetentionAction.DELETE.value
    )
    status: Mapped[str] = mapped_column(
        String(16), default=PolicyStatus.ACTIVE.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ModelPolicy(Base):
    """V40-014: which model providers/models may process a sensitivity level."""

    __tablename__ = "model_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    sensitivity_level: Mapped[str] = mapped_column(
        String(16), default=SensitivityLevel.INTERNAL.value, index=True
    )
    allowed_providers_json: Mapped[str] = mapped_column(Text, default="[]")
    allowed_models_json: Mapped[str] = mapped_column(Text, default="[]")
    redaction_required: Mapped[bool] = mapped_column(default=False)
    persistence_allowed: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(
        String(16), default=PolicyStatus.ACTIVE.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ModelUsageLedger(Base):
    """V40-015: per-operation model/runtime usage + cost accounting."""

    __tablename__ = "model_usage_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    operation_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    model_ref: Mapped[str] = mapped_column(String(128), default="")
    input_units: Mapped[int] = mapped_column(Integer, default=0)
    output_units: Mapped[int] = mapped_column(Integer, default=0)
    cost_amount: Mapped[float | None] = mapped_column(default=None)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class GovernanceException(Base):
    """V40-011: a time-boxed exception to a governance rule (approved/expired)."""

    __tablename__ = "governance_exceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    exception_type: Mapped[str] = mapped_column(String(64), default="")
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[int | None] = mapped_column(Integer, default=None)
    reason: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    approved_by: Mapped[int | None] = mapped_column(Integer, default=None)
    status: Mapped[str] = mapped_column(
        String(16), default=GovernanceExceptionStatus.OPEN.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DrTestRun(Base):
    """V40-017: a recorded disaster-recovery drill with RTO/RPO evidence."""

    __tablename__ = "dr_test_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    test_type: Mapped[str] = mapped_column(
        String(32), default=DrTestType.BACKUP_RESTORE.value, index=True
    )
    environment: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(
        String(16), default=DrTestStatus.PENDING.value, index=True
    )
    rto_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    rpo_seconds: Mapped[int | None] = mapped_column(Integer, default=None)
    evidence_uri: Mapped[str] = mapped_column(Text, default="")
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
