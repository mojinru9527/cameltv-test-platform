"""AITDE V3.4 Durable Runtime models (V34).

Data model for the Temporal + Network Worker + Security Plane foundation
(plan §§3-6). These tables are created by the M34 alembic migration; all are
``String``-valued enums so they stay stable across SQLite/PostgreSQL.
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
    ApprovalStatus,
    Capability,
    IdempotencyStatus,
    NetworkZone,
    PolicyDecision,
    PolicyType,
    RuntimeResourceType,
    SecretRefStatus,
    WorkflowStatus,
    WorkflowType,
    WorkerStatus,
)


class WorkerNode(Base):
    """V34-003: a registered runtime worker. LLM never selects a machine."""

    __tablename__ = "worker_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    network_zone: Mapped[str] = mapped_column(
        String(16), default=NetworkZone.TEST.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=WorkerStatus.OFFLINE.value, index=True
    )
    version: Mapped[str] = mapped_column(String(64), default="")
    machine_identity: Mapped[str] = mapped_column(String(128), default="")
    tags_json: Mapped[str] = mapped_column(Text, default="{}")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    registered_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class WorkerCapability(Base):
    """V34-004: a capability a worker can serve for TaskQueue routing."""

    __tablename__ = "worker_capabilities"
    __table_args__ = (
        UniqueConstraint("worker_id", "capability", name="uq_worker_capability"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(Integer, index=True)
    capability: Mapped[str] = mapped_column(
        String(16), default=Capability.HTTP.value, index=True
    )
    version: Mapped[str] = mapped_column(String(64), default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")


class WorkflowRun(Base):
    """V34-002: one durable workflow run bound to a Temporal workflow id."""

    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    run_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    workflow_type: Mapped[str] = mapped_column(
        String(32), default=WorkflowType.SCENARIO_EXECUTION.value, index=True
    )
    temporal_namespace: Mapped[str] = mapped_column(String(64), default="default")
    temporal_workflow_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    temporal_run_id: Mapped[str | None] = mapped_column(String(128), default=None)
    status: Mapped[str] = mapped_column(
        String(16), default=WorkflowStatus.SCHEDULED.value, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class RuntimeIdempotencyKey(Base):
    """V34-012: protects Run/Data/Cleanup/Activity from duplicate delivery."""

    __tablename__ = "runtime_idempotency_keys"
    __table_args__ = (
        UniqueConstraint("scope", "key_hash", name="uq_idempotency_scope_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), default="default", index=True)
    key_hash: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(
        String(16), default=RuntimeResourceType.ACTIVITY.value
    )
    resource_id: Mapped[int | None] = mapped_column(Integer, default=None)
    status: Mapped[str] = mapped_column(
        String(16), default=IdempotencyStatus.PENDING.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class PolicyProfile(Base):
    """V34-010: a versioned policy document (OPA or self-built adapter)."""

    __tablename__ = "policy_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    policy_type: Mapped[str] = mapped_column(
        String(32), default=PolicyType.DRIVER_ACTION.value, index=True
    )
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    document_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class PolicyBinding(Base):
    """V34-010: bind a policy profile to a project/environment/zone at priority."""

    __tablename__ = "policy_bindings"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    environment_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    network_zone: Mapped[str] = mapped_column(
        String(16), default=NetworkZone.TEST.value, index=True
    )
    policy_profile_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)


class SecretRef(Base):
    """V34-008: secret metadata only; the value is resolved on the worker."""

    __tablename__ = "secret_refs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    provider: Mapped[str] = mapped_column(String(32), default="env")
    external_ref: Mapped[str] = mapped_column(String(256), default="")
    purpose: Mapped[str] = mapped_column(String(64), default="")
    scope_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(
        String(16), default=SecretRefStatus.ACTIVE.value, index=True
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ApprovalRequest(Base):
    """V34-011: REQUIRE_APPROVAL persistence; approve/reject signals the workflow."""

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    run_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    action_type: Mapped[str] = mapped_column(String(64), default="")
    request_json: Mapped[str] = mapped_column(Text, default="{}")
    policy_decision: Mapped[str] = mapped_column(
        String(16), default=PolicyDecision.REQUIRE_APPROVAL.value
    )
    status: Mapped[str] = mapped_column(
        String(16), default=ApprovalStatus.PENDING.value, index=True
    )
    requested_by: Mapped[int] = mapped_column(Integer, default=0)
    approved_by: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
