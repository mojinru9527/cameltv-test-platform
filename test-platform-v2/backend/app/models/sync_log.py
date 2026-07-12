"""SyncLog model — audit trail for external integration sync attempts."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int] = mapped_column(default=0, index=True)
    defect_id: Mapped[int] = mapped_column(default=0, index=True)
    direction: Mapped[str] = mapped_column(String(10), default="push")  # "push" | "pull"
    status: Mapped[str] = mapped_column(String(20), default="success")  # "success" | "failed" | "skipped"
    external_id: Mapped[str] = mapped_column(String(100), default="")  # issue key from external system
    message: Mapped[str] = mapped_column(Text, default="")  # human-readable detail / error
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
