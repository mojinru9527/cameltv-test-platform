from __future__ import annotations
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


class AssetType(StrEnum):
    API = "api"
    UI = "ui"
    SCRIPT = "script"
    EXTERNAL = "external"


class CampaignRunRequest(BaseModel):
    environment_id: int
    runner_selector: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=128)


class ExecutionClaimRequest(BaseModel):
    runner_id: str = Field(min_length=1, max_length=128)
    capabilities: dict[str, Any] = Field(default_factory=dict)


class ExecutionReportRequest(BaseModel):
    runner_id: str = Field(min_length=1, max_length=128)
    runtime_status: str
    outcome: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str = Field(default="", max_length=4000)
