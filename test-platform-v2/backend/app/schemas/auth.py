"""鉴权相关 Pydantic 模型 —— 同时是 OpenAPI 契约来源。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    username: str
    password: str


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


class MeOut(BaseModel):
    user: UserBrief
    projects: list[ProjectBrief] = []
    permissions: list[str] = []
    current_project_id: int | None = None


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, description="新密码，最少 6 位")
