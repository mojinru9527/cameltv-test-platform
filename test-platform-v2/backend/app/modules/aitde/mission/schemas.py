"""Mission Pydantic schemas (V30-013).

Keep the API contract explicit. ``MissionCreate`` mirrors the 3-step wizard's
Step-1 fields; ``mission_type``/``status`` are string-valued enums for stability.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.aitde.common.enums import (
    AcceptanceStatus,
    MissionStatus,
    MissionType,
)


class MissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    mission_type: MissionType = MissionType.VERSION
    version_label: str | None = Field(default=None, max_length=64)
    qa_owner_id: int | None = None
    default_environment_id: int | None = None


class MissionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    version_label: str | None = Field(default=None, max_length=64)
    owner_id: int | None = None
    qa_owner_id: int | None = None
    default_environment_id: int | None = None
    # 状态迁移由 service 做生命周期校验，禁止非法跳转（如 DRAFT → CONTRACT_FROZEN）。
    status: MissionStatus | None = None
    acceptance_status: AcceptanceStatus | None = None


class MissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_key: str
    mission_type: str
    title: str
    version_label: str | None = None
    status: str
    owner_id: int | None = None
    qa_owner_id: int | None = None
    default_environment_id: int | None = None
    current_contract_version_id: int | None = None
    acceptance_status: str
    legacy_version_mission_id: int | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime | None = None
    archived_at: datetime | None = None


class MissionListParams(BaseModel):
    status: str | None = None
    mission_type: str | None = None
    keyword: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


ARCHIVED_STATUSES: set[str] = {MissionStatus.ARCHIVED.value}
ACTIVE_STATUSES: set[str] = {
    s.value for s in MissionStatus if s.value != MissionStatus.ARCHIVED.value
}
