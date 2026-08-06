"""项目相关 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str = ""
    status: int = 1
    owner_id: int = 0
    organization_id: int | None = None
    organization_name: str = ""


class ProjectCreate(BaseModel):
    code: str
    name: str
    description: str = ""
    organization_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class SwitchProjectIn(BaseModel):
    project_id: int


class ProjectInviteIn(BaseModel):
    usage_limit: int = 1
    expires_at: Optional[datetime] = None


class ProjectInviteOut(BaseModel):
    id: int
    project_id: int
    token: str
    url: str = ""
    usage_limit: int = 1
    used_count: int = 0
    expires_at: Optional[datetime] = None
    status: int = 1
    created_at: Optional[datetime] = None
