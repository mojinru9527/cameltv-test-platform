"""鉴权相关 Pydantic 模型 —— 同时是 OpenAPI 契约来源。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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


class MeOut(BaseModel):
    user: UserBrief
    projects: list[ProjectBrief] = []
    permissions: list[str] = []
    current_project_id: int | None = None
