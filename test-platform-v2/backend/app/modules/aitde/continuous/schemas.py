"""AITDE V3.5 Continuous Acceptance API schemas (V35)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.aitde.common.enums import (
    CampaignType,
    ContinuousTriggerType,
    FingerprintSourceType,
)


class FingerprintCaptureIn(BaseModel):
    """Capture a fingerprint for an environment (V35-001)."""

    build_label: str | None = Field(default=None, max_length=128)
    components: dict = Field(default_factory=dict)
    source_type: FingerprintSourceType = FingerprintSourceType.AUTO


class FingerprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    environment_id: int
    fingerprint_hash: str
    build_label: str | None = None
    components_json: str = "{}"
    source_type: str
    captured_at: datetime | None = None


class BuildObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    environment_id: int
    fingerprint_id: int
    previous_fingerprint_id: int | None = None
    change_summary_json: str = "{}"
    detected_at: datetime | None = None
    status: str


class CampaignCreateIn(BaseModel):
    mission_id: int
    environment_id: int
    name: str = Field(default="", max_length=128)
    campaign_type: CampaignType = CampaignType.IMPACTED
    project_id: int = 0
    scenarios: list[dict] = Field(default_factory=list)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_id: int
    name: str
    campaign_type: str
    environment_id: int
    build_observation_id: int | None = None
    status: str
    created_by_type: str
    created_at: datetime | None = None


class RunProfileIn(BaseModel):
    project_id: int = 0
    name: str = Field(default="", max_length=128)
    selector: dict = Field(default_factory=dict)
    evidence_policy: dict = Field(default_factory=dict)
    retry_policy: dict = Field(default_factory=dict)
    parallelism: int = 1


class RunProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    selector_json: str = "{}"
    evidence_policy_json: str = "{}"
    retry_policy_json: str = "{}"
    parallelism: int = 1
    status: str


class TriggerIn(BaseModel):
    project_id: int = 0
    mission_id: int | None = None
    trigger_type: ContinuousTriggerType = ContinuousTriggerType.MANUAL
    config: dict = Field(default_factory=dict)


class TriggerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_id: int | None = None
    trigger_type: str
    config_json: str = "{}"
    status: str
    last_fired_at: datetime | None = None
    created_at: datetime | None = None


class GateEvaluateIn(BaseModel):
    project_id: int = 0
    build_observation_id: int | None = None
    campaign_id: int | None = None


class GateResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    campaign_id: int | None = None
    build_observation_id: int | None = None
    policy_id: int
    result: str
    checks_json: str = "[]"
    evaluated_at: datetime | None = None
    override_status: str | None = None
    override_by: int | None = None
    override_reason: str | None = None


class GateOverrideIn(BaseModel):
    override_status: str
    override_by: int = 0
    override_reason: str = Field(default="", max_length=2000)
