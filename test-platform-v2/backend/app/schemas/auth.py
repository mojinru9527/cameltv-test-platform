"""鉴权相关 Pydantic 模型 —— 同时是 OpenAPI 契约来源。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.organization import OrganizationBrief
from app.schemas.system import MenuOut


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    nickname: str = ""
    email: str = ""
    password: str = Field(..., min_length=6, max_length=128)
    invite_code: str = ""
    project_invite_token: str = ""


class PublicAccessOut(BaseModel):
    """未登录访客可安全读取的平台入口配置。"""

    registration_enabled: bool
    invite_code_required: bool
    modules: list[MenuOut] = Field(default_factory=list)


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str = ""
    email: str = ""


class ProjectBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBrief
    projects: list[ProjectBrief] = []
    permissions: list[str] = []
    must_change_password: bool = False  # 首次登录使用默认密码时要求强制修改
    organizations: list[OrganizationBrief] = []


class MeOut(BaseModel):
    user: UserBrief
    projects: list[ProjectBrief] = []
    permissions: list[str] = []
    current_project_id: int | None = None
    organizations: list[OrganizationBrief] = []


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, description="新密码，最少 6 位")
