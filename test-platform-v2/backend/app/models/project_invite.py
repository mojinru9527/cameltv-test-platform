"""项目邀请链接模型（Batch 106：同事凭链接注册即入项目）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ProjectInvite(Base, TimestampMixin):
    __tablename__ = "sys_project_invite"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    token: Mapped[str] = mapped_column(unique=True, index=True)
    created_by: Mapped[int] = mapped_column(default=0)
    usage_limit: Mapped[int] = mapped_column(default=1)
    used_count: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    # 1=启用 0=停用
    status: Mapped[int] = mapped_column(default=1)
