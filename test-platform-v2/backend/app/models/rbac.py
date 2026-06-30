"""RBAC 模型 — 角色 / 权限 / 关联表。"""
from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column()
    # 数据范围：global=全局 / project=本项目 / self=仅自己
    data_scope: Mapped[str] = mapped_column(default="project")
    remark: Mapped[str] = mapped_column(default="")


class Permission(Base):
    __tablename__ = "sys_permission"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 权限点编码，如 menu:testcase / case:list / case:create
    code: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column()
    # menu=菜单 button=按钮 api=接口
    type: Mapped[str] = mapped_column(default="menu")
    parent_id: Mapped[int] = mapped_column(default=0)
    # 前端路由路径（菜单类型用）
    path: Mapped[str] = mapped_column(default="")
    icon: Mapped[str] = mapped_column(default="")
    sort: Mapped[int] = mapped_column(default=0)


class UserRole(Base):
    __tablename__ = "sys_user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", "project_id", name="uq_user_role_project"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    role_id: Mapped[int] = mapped_column()
    # 0=全局角色；>0=该项目内角色
    project_id: Mapped[int] = mapped_column(default=0)


class RolePermission(Base):
    __tablename__ = "sys_role_permission"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(index=True)
    permission_id: Mapped[int] = mapped_column()
