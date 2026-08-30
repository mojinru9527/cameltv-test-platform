"""AITDE V3.4 API schemas (V34)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.aitde.common.enums import (
    Capability,
    NetworkZone,
    PolicyDecision,
    PolicyType,
)


# ── WorkerNode ───────────────────────────────────────────────────────────────


class WorkerHeartbeatIn(BaseModel):
    worker_key: str = Field(min_length=1, max_length=64)
    name: str = Field(default="", max_length=128)
    network_zone: NetworkZone = NetworkZone.TEST
    version: str = Field(default="", max_length=64)
    machine_identity: str = Field(default="", max_length=128)
    tags: dict = Field(default_factory=dict)
    capabilities: list[Capability] = Field(default_factory=list)


class WorkerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_key: str
    name: str
    network_zone: str
    status: str
    version: str
    machine_identity: str
    tags_json: str = "{}"
    last_heartbeat_at: datetime | None = None
    registered_at: datetime | None = None


# ── WorkflowRun ─────────────────────────────────────────────────────────────


class WorkflowRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_id: int | None = None
    run_id: int | None = None
    workflow_type: str
    temporal_namespace: str
    temporal_workflow_id: str
    temporal_run_id: str | None = None
    status: str
    started_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None


class RunResumeIn(BaseModel):
    """Resume a WAITING_APPROVAL / WAITING_WORKER / FAILED run."""

    workflow_id: str = Field(min_length=1, max_length=128)
    signal_name: str = Field(default="resume", max_length=64)
    args: dict = Field(default_factory=dict)


# ── Policy / SecretRef / Approval ───────────────────────────────────────────


class PolicyProfileIn(BaseModel):
    project_id: int = 0
    name: str = Field(default="", max_length=128)
    policy_type: PolicyType = PolicyType.DRIVER_ACTION
    version: str = Field(default="1.0", max_length=32)
    document: dict = Field(default_factory=dict)


class PolicyProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None = None
    name: str
    policy_type: str
    version: str
    document_json: str = "{}"
    status: str
    created_at: datetime | None = None


class SecretRefIn(BaseModel):
    project_id: int = 0
    name: str = Field(default="", max_length=128)
    provider: str = Field(default="env", max_length=32)
    external_ref: str = Field(default="", max_length=256)
    purpose: str = Field(default="", max_length=64)
    scope: dict = Field(default_factory=dict)


class SecretRefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    provider: str
    external_ref: str
    purpose: str
    scope_json: str = "{}"
    status: str
    rotated_at: datetime | None = None
    created_at: datetime | None = None


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_id: int | None = None
    run_id: int | None = None
    action_type: str
    request_json: str = "{}"
    policy_decision: str
    status: str
    requested_by: int
    approved_by: int | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class PolicyDecisionIn(BaseModel):
    """Policy Gateway request (plan §6)."""

    actor: str = Field(default="user", max_length=32)
    project_id: int = 1
    environment_id: int | None = None
    network_zone: NetworkZone = NetworkZone.TEST
    driver: str = Field(default="", max_length=64)
    action: str = Field(default="", max_length=64)
    target: dict = Field(default_factory=dict)


class PolicyDecisionOut(BaseModel):
    decision: PolicyDecision = PolicyDecision.ALLOW
    reason: str = ""


class ApprovalResolveIn(BaseModel):
    approved_by: int = 0
