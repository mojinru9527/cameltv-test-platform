"""AITDE V3.6 production API schemas (V36-013/014)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.modules.aitde.common.enums import (
    ObservationMode,
)


class ObservationSessionCreate(BaseModel):
    project_id: int
    environment_id: int
    mission_id: int | None = None
    worker_id: int | None = None
    mode: ObservationMode = ObservationMode.OBSERVE
    started_by: int = 0
    policy_version: str = "1.0"


class ObservationSessionRead(BaseModel):
    id: int
    project_id: int
    mission_id: int | None = None
    environment_id: int
    worker_id: int | None = None
    mode: str
    status: str
    policy_version: str
    started_by: int | None = None
    started_at: str | None = None
    finished_at: str | None = None


class JourneyRead(BaseModel):
    id: int
    project_id: int
    session_id: int
    name: str
    journey_hash: str
    summary_json: str
    source_ref_json: str
    created_at: str | None = None


class JourneyStepRead(BaseModel):
    id: int
    journey_id: int
    sequence: int
    event_type: str
    semantic_action_json: str
    url_template: str
    xhr_refs_json: str
    evidence_refs_json: str
    timestamp: str | None = None


class JourneyDetailRead(JourneyRead):
    steps: list[JourneyStepRead] = []


class DbInspectRequest(BaseModel):
    project_id: int
    data_source_id: int
    sql: str = Field(..., min_length=1)
    schema_name: str | None = None
    session_id: int | None = None
    table_names: list[str] = []


class DbInspectResponse(BaseModel):
    rows: list[dict[str, Any]] = []
    row_count: int
    duration_ms: int


class QueryAuditRead(BaseModel):
    id: int
    project_id: int
    session_id: int | None = None
    data_source_id: int
    query_fingerprint: str
    operation_type: str
    schema_name: str | None = None
    table_names_json: str
    row_count: int
    duration_ms: int
    policy_decision: str
    executed_at: str | None = None


class EntityGraphExtractRequest(BaseModel):
    project_id: int
    root_entity_type: str
    root_ref_hash: str
    source_environment_id: int
    mission_id: int | None = None


class TemplateBuildRequest(BaseModel):
    project_id: int
    name: str
    entity_graph_snapshot_id: int
    masking_profile_id: int | None = None
    mission_id: int | None = None
    created_by: int = 0


class TemplateValidateRequest(BaseModel):
    project_id: int
    template_id: int


class TemplateMaterializeRequest(BaseModel):
    project_id: int
    template_id: int
    target_environment_id: int


class GapAnalysisRequest(BaseModel):
    project_id: int
    journey_id: int


class GapProposalRead(BaseModel):
    kind: str
    title: str
    confidence: str
    evidence: str = ""
    auto_approved: bool = False


class MaskRuleCreate(BaseModel):
    profile_id: int
    entity_pattern: str = "*"
    field_pattern: str = "*"
    classification: str = "PII"
    strategy: str = "HASH"
    config_json: dict[str, Any] = {}
    priority: int = 0
