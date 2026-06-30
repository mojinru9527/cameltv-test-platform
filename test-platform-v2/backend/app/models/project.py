"""项目 / 项目成员模型 — 多项目隔离的载体。"""
from __future__ import annotations

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "sys_project"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column(default="")
    owner_id: Mapped[int] = mapped_column(default=0)
    status: Mapped[int] = mapped_column(default=1)
    # 项目级配置（JSON 文本）：环境/代理等
    config: Mapped[str] = mapped_column(default="{}")


class ProjectMember(Base):
    __tablename__ = "sys_project_member"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(index=True)
    role_id: Mapped[int] = mapped_column(default=0)
