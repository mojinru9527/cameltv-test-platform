"""Schemas for version mission orchestration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VersionMissionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., min_length=1, max_length=80)
    requirement_url: str = ""
    test_env_url: str = ""
    admin_env_url: str = ""
    environment_id: int | None = None
    requirement_doc_id: int | None = None
    test_plan_id: int | None = None
    scope: dict[str, Any] = Field(default_factory=dict)
    qa_owner_id: int = 0


class VersionMissionUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    version: str | None = Field(None, max_length=80)
    requirement_url: str | None = None
    test_env_url: str | None = None
    admin_env_url: str | None = None
    environment_id: int | None = None
    requirement_doc_id: int | None = None
    test_plan_id: int | None = None
    status: str | None = None
    scope: dict[str, Any] | None = None
    summary: str | None = None
    qa_owner_id: int | None = None


class AgentWorkLogCreate(BaseModel):
    department: str = Field(..., min_length=1, max_length=80)
    agent_name: str = Field(..., min_length=1, max_length=120)
    action: str = Field(..., min_length=1, max_length=120)
    status: str = "done"
    input_ref: str = ""
    output_ref: str = ""
    detail: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


class OpenApiGenerateRequest(BaseModel):
    spec: dict[str, Any] = Field(default_factory=dict)
    source_name: str = "swagger"
    import_to_case_library: bool = True
    only_changed: bool = False


class TrafficGenerateRequest(BaseModel):
    traffic: list[dict[str, Any]] = Field(default_factory=list)
    source_name: str = "ui-capture"
    import_to_case_library: bool = True


class UiDraftGenerateRequest(BaseModel):
    priorities: list[str] = Field(default_factory=lambda: ["P0", "P1"])
    write_specs: bool = True
    max_cases: int = Field(default=30, ge=1, le=200)


class QualityGateOut(BaseModel):
    mission_id: int
    status: str
    passed: bool
    score: int
    checks: list[dict[str, Any]]
    summary: dict[str, Any]


class VersionMissionOut(BaseModel):
    id: int
    project_id: int
    mission_key: str
    title: str
    version: str
    requirement_url: str
    test_env_url: str
    admin_env_url: str
    environment_id: int | None
    requirement_doc_id: int | None
    test_plan_id: int | None
    status: str
    scope: dict[str, Any]
    summary: str
    created_by: int
    qa_owner_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentWorkLogOut(BaseModel):
    id: int
    project_id: int
    mission_id: int
    department: str
    agent_name: str
    action: str
    status: str
    input_ref: str
    output_ref: str
    detail: str
    payload: dict[str, Any]
    duration_ms: int
    created_at: datetime | None = None


class GeneratedArtifactOut(BaseModel):
    id: int
    project_id: int
    mission_id: int
    artifact_type: str
    source: str
    name: str
    ref_id: str
    content: str
    meta: dict[str, Any]
    created_at: datetime | None = None
