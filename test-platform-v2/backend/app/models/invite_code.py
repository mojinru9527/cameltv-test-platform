"""注册邀请码模型（Batch 104 外放轻量模式）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class InviteCode(Base, TimestampMixin):
    __tablename__ = "sys_invite_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    created_by: Mapped[int] = mapped_column(default=0)
    usage_limit: Mapped[int] = mapped_column(default=1)
    used_count: Mapped[int] = mapped_column(default=0)
    # 空 = 永不过期；非空按 UTC（naive）比较
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    # 1=启用 0=停用
    status: Mapped[int] = mapped_column(default=1)
