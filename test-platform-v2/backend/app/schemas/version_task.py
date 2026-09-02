"""Schemas for VersionTask (B6 unified fact source)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _json_to_dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v) if v.strip() else {}
        except (TypeError, ValueError):
            return {}
    return {}


class VersionTaskCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=300)
    version: str = Field(..., min_length=1, max_length=80)
    source: str = Field(default="manual", max_length=20)
    source_mission_id: int | None = None
    source_bundle_id: int | None = None
    requirement_doc_id: int | None = None
    release_bundle_id: int | None = None
    environment_id: int | None = None
    scope: dict[str, Any] = Field(default_factory=dict)
    qa_owner_id: int = 0


class VersionTaskUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str | None = Field(None, max_length=300)
    version: str | None = Field(None, max_length=80)
    requirement_doc_id: int | None = None
    release_bundle_id: int | None = None
    environment_id: int | None = None
    scope: dict[str, Any] | None = None
    summary: str | None = None
    qa_owner_id: int | None = None


class VersionTaskTransition(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., min_length=1, max_length=30)
    verdict: str = Field(default="", max_length=20)
    summary: str | None = None


class ExecutionLinkIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    execution_type: str = Field(default="runner", max_length=30)
    execution_id: int = Field(..., ge=1)
    ref: str = Field(default="", max_length=120)


class DefectLinkIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    defect_id: int = Field(..., ge=1)


class VersionTaskExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_type: str = ""
    execution_id: int = 0
    ref: str = ""


class VersionTaskDefectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    defect_id: int = 0


class VersionTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    title: str = ""
    version: str = ""
    source: str = "manual"
    source_mission_id: int | None = None
    source_bundle_id: int | None = None
    requirement_doc_id: int | None = None
    release_bundle_id: int | None = None
    environment_id: int | None = None
    status: str = "draft"
    verdict: str = ""
    coverage: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    scope: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    created_by: int = 0
    qa_owner_id: int = 0
    executions: list[VersionTaskExecutionOut] = Field(default_factory=list)
    defects: list[VersionTaskDefectOut] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("coverage", "scope", "risk", mode="before")
    @classmethod
    def _parse_json(cls, v: Any) -> dict[str, Any]:
        return _json_to_dict(v)


class VersionTaskListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    title: str = ""
    version: str = ""
    source: str = "manual"
    status: str = "draft"
    verdict: str = ""
    release_bundle_id: int | None = None
    requirement_doc_id: int | None = None
    qa_owner_id: int = 0
    created_at: datetime | None = None


class PlanItemCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_type: str = Field(default="functional", max_length=30)
    title: str = Field(..., min_length=1, max_length=300)
    description: str = ""
    confidence: int = Field(default=0, ge=0, le=100)
    question: str = ""


class PlanItemReview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str = Field(...)  # adopt / modify / remove / ask / confirm
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    confidence: int | None = Field(None, ge=0, le=100)
    question: str | None = None
    answer: str | None = None


class PlanItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: str = "functional"
    title: str = ""
    description: str = ""
    confidence: int = 0
    status: str = "draft"
    question: str = ""
    answer: str = ""
    order_index: int = 0


class VersionTaskRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int = 0
    status: str = "pending"
    progress: int = 0
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    blocked: int = 0
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("evidence", "failures", mode="before")
    @classmethod
    def _json_list(cls, v: Any) -> list[dict[str, Any]]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v) if v.strip() else []
            except (TypeError, ValueError):
                return []
        return []


class ReleaseRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verdict: str = Field(..., max_length=20)  # pass / blocked / conditional
    release_bundle_id: int | None = None
    risk: list[str] = Field(default_factory=list)
    summary: str | None = None
