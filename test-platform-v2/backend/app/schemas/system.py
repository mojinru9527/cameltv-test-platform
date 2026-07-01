"""系统管理 Pydantic 模型 —— 用户 / 角色 / 权限 / 审计 + 菜单。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── 菜单 ──

class MenuOut(BaseModel):
    code: str
    name: str
    path: str = ""
    icon: str = ""
    sort: int = 0
    children: list["MenuOut"] = []


MenuOut.model_rebuild()


# ── 用户 ──

class UserBrief(BaseModel):
    """兼容 auth schema 的同名模型；system 侧有更完整版。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nickname: str
    email: str
    status: int = 1


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nickname: str = ""
    email: str = ""
    status: int = 1
    # 关联的角色 code 列表（填入 UserRole 中 global + 该 project 的角色）
    role_codes: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class UserCreate(BaseModel):
    username: str
    password: str = Field(..., min_length=6, description="密码，最少 6 位，无默认值")
    nickname: str = ""
    email: str = ""
    status: int = 1
    role_codes: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    username: str | None = None
    nickname: str | None = None
    email: str | None = None
    status: int | None = None
    password: str | None = None      # 不填则不修改密码
    role_codes: list[str] | None = None


# ── 角色 ──

class RoleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    data_scope: str = "project"
    remark: str = ""
    permission_codes: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class RoleCreate(BaseModel):
    code: str
    name: str
    data_scope: str = "project"
    remark: str = ""
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = None
    data_scope: str | None = None
    remark: str | None = None
    permission_codes: list[str] | None = None


# ── 权限 ──

class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    type: str = "menu"
    parent_id: int = 0
    path: str = ""
    icon: str = ""
    sort: int = 0


class PermissionGroup(BaseModel):
    """按分组整理的权限列表，前端 Checkbox 用。"""
    group: str = ""
    items: list["PermissionOut"] = Field(default_factory=list)


# ── 审计 ──

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int = 0
    username: str = ""
    project_id: int = 0
    action: str = ""
    target: str = ""
    detail: str = ""
    ip: str = ""
    created_at: datetime | None = None
