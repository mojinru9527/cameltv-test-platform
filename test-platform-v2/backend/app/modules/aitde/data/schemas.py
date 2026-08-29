"""AITDE V3.2 DataSource schemas (V32-001)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.modules.aitde.common.enums import (
    DataPlanStrategy,
    DataRequirementCleanupPolicy,
    DataRequirementSharingPolicy,
    DataSourceAccessMode,
    DataSourceType,
)


class DataSourceCreate(BaseModel):
    source_type: DataSourceType
    name: str = Field(..., max_length=255)
    environment_id: int | None = None
    network_zone: str = Field(default="", max_length=64)
    secret_ref: str | None = Field(default=None, max_length=255)
    access_mode: DataSourceAccessMode = DataSourceAccessMode.READONLY
    # Connection metadata (host/database/table set etc). Never stores secrets.
    config: dict[str, Any] | None = None
    policy_ref: str | None = Field(default=None, max_length=255)


class DataSourceRead(BaseModel):
    id: int
    project_id: int
    environment_id: int | None = None
    source_type: str
    name: str
    network_zone: str
    # A reference to the secret, never the secret value it points at.
    secret_ref: str | None = None
    access_mode: str
    config_json: str
    policy_ref: str | None = None
    status: str
    created_by: int
    created_at: str | None = None
    updated_at: str | None = None


class DataRequirementRead(BaseModel):
    id: int
    scenario_version_id: int
    requirement_key: str
    entity_type: str
    constraints_json: str
    required: bool
    sharing_policy: str
    cleanup_policy: str
    source_refs_json: str
    created_at: str | None = None


class DataRequirementUpdate(BaseModel):
    """Tester 修订（PATCH）— 只允许修订业务描述，绝不生成 SQL。"""

    entity_type: str | None = Field(default=None, max_length=64)
    constraints: dict[str, Any] | None = None
    required: bool | None = None
    sharing_policy: DataRequirementSharingPolicy | None = None
    cleanup_policy: DataRequirementCleanupPolicy | None = None


class DataRequirementDeriveRequest(BaseModel):
    """AI 派生候选数据需求。V32-002 规则式实现；请求体保留占位。"""

    pass


class DataPlanGenerateRequest(BaseModel):
    """生成数据计划（V32-003）。环境 + 可选策略提示。"""

    environment_id: int | None = None
    strategy: DataPlanStrategy | None = None


class DataPlanStepRead(BaseModel):
    id: int
    data_plan_id: int
    sequence: int
    step_type: str
    driver: str
    command_json: str
    compensation_json: str | None = None
    status: str


class DataPlanRead(BaseModel):
    id: int
    scenario_version_id: int
    environment_id: int | None = None
    status: str
    strategy: str
    plan_hash: str
    risk_level: str
    created_by_type: str
    created_at: str | None = None
    approved_by: int | None = None
    approved_at: str | None = None
    steps: list[DataPlanStepRead] = []
