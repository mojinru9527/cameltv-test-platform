"""组织相关 Pydantic 模型（Batch 105 租户模式）。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=1, max_length=64)
    description: str = ""


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str = ""
    type: str = "team"
    owner_id: int = 0
    my_role: int = 3
    status: int = 1
    member_count: int = 0
    project_count: int = 0


class OrganizationMemberOut(BaseModel):
    organization_id: int
    user_id: int
    role_id: int = 3
    username: str = ""
    nickname: str = ""


class OrganizationBrief(BaseModel):
    id: int
    code: str
    name: str
    type: str = "team"
