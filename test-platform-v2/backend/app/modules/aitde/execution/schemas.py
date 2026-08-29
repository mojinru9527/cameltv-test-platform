"""AITDE V3.1 execution schemas (V31).

Keep the API contract explicit and string-valued-enum based, matching V3.0.
Adapters and EnvironmentSnapshot are the PR31-01 surface; run/step/assertion
schemas land in PR31-02 (added to this module as the version grows).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.aitde.common.enums import AdapterStatus, AdapterType, TriggerType


# ── ScenarioAdapter (PR31-01) ────────────────────────────────────────────────


class AdapterCreate(BaseModel):
    scenario_version_id: int
    adapter_type: AdapterType = AdapterType.API
    source_asset_type: str | None = Field(default=None, max_length=64)
    source_asset_id: int | None = None
    config: dict = Field(default_factory=dict)
    adapter_version: str = Field(default="1.0", min_length=1, max_length=64)


class AdapterUpdate(BaseModel):
    status: AdapterStatus | None = None
    config: dict | None = None
    adapter_version: str | None = Field(default=None, min_length=1, max_length=64)


class AdapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    scenario_version_id: int
    adapter_type: str
    status: str
    source_asset_type: str | None = None
    source_asset_id: int | None = None
    config_json: str = "{}"
    adapter_version: str
    created_by: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── EnvironmentSnapshot (PR31-01) ────────────────────────────────────────────


class EnvironmentSnapshotCreate(BaseModel):
    build_label: str | None = Field(default=None, max_length=128)
    frontend_version: str | None = Field(default=None, max_length=64)
    service_versions: dict = Field(default_factory=dict)
    openapi_hash: str | None = Field(default=None, max_length=64)
    db_schema_version: str | None = Field(default=None, max_length=64)
    config_hash: str | None = Field(default=None, max_length=64)
    static_asset_hash: str | None = Field(default=None, max_length=64)
    manual_note: str | None = None


class EnvironmentSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    environment_id: int
    mission_id: int
    build_label: str | None = None
    frontend_version: str | None = None
    service_versions_json: str = "{}"
    openapi_hash: str | None = None
    db_schema_version: str | None = None
    config_hash: str | None = None
    static_asset_hash: str | None = None
    manual_note: str | None = None
    fingerprint_hash: str
    captured_at: datetime | None = None
    created_by_type: str = "AUTO"


# ── ExecutionRun (PR31-02) ───────────────────────────────────────────────────


class RunCreate(BaseModel):
    mission_id: int
    scenario_id: int
    scenario_version_id: int
    contract_version_id: int
    adapter_id: int | None = None
    environment_id: int
    environment_snapshot_id: int
    trigger_type: TriggerType = TriggerType.MANUAL


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_id: int
    scenario_id: int
    scenario_version_id: int
    contract_version_id: int
    adapter_id: int | None = None
    environment_id: int
    environment_snapshot_id: int | None = None
    runtime_status: str
    outcome: str | None = None
    evidence_status: str
    trigger_type: str
    parent_run_id: int | None = None
    retry_no: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    created_by: int
    created_at: datetime | None = None


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    sequence: int
    step_key: str
    step_type: str
    status: str
    error_type: str | None = None
    error_message: str | None = None
    input_snapshot_json: str | None = None
    output_snapshot_json: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AssertionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    step_id: int | None = None
    oracle_id: int
    oracle_snapshot_json: str = "{}"
    expected_json: str = "{}"
    actual_json: str = "{}"
    result: str
    reason_code: str = ""
    evidence_refs_json: str = "[]"
    evaluated_at: datetime | None = None


class ShadowAuditCreate(BaseModel):
    audit_outcome: str = Field(min_length=1, max_length=16)
    reason: str = Field(default="", max_length=2000)
