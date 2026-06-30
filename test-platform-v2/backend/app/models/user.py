"""用户模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str] = mapped_column()
    nickname: Mapped[str] = mapped_column(default="")
    email: Mapped[str] = mapped_column(default="")
    # 1=启用 0=禁用
    status: Mapped[int] = mapped_column(default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)
