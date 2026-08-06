"""组织 / 组织成员模型（Batch 105 租户模式：用户 → 组织 → 项目）。"""
from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "sys_organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column(default="")
    # personal=个人组织（注册自动创建，不可停用） / team=团队组织
    type: Mapped[str] = mapped_column(default="team")
    owner_id: Mapped[int] = mapped_column(default=0)
    # 1=启用 0=停用
    status: Mapped[int] = mapped_column(default=1)


class OrganizationMember(Base):
    __tablename__ = "sys_organization_member"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(index=True)
    # 1=负责人 2=管理员 3=成员
    role_id: Mapped[int] = mapped_column(default=3)
