"""审计日志模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditLog(Base):
    __tablename__ = "sys_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(default=0)
    username: Mapped[str] = mapped_column(default="")
    project_id: Mapped[int] = mapped_column(default=0)
    action: Mapped[str] = mapped_column(default="")
    target: Mapped[str] = mapped_column(default="")
    detail: Mapped[str] = mapped_column(default="")
    ip: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
