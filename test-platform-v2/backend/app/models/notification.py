"""Notification configuration model — per-project webhook channels."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class NotificationChannel(Base):
    """Per-project webhook channel (feishu/dingtalk/wecom_work)."""

    __tablename__ = "notification_channel"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    channel_type: Mapped[str] = mapped_column(String(20), default="webhook")  # webhook/email/sms
    provider: Mapped[str] = mapped_column(String(30), default="generic")      # feishu/dingtalk/wecom_work/generic
    webhook_url: Mapped[str] = mapped_column(String(500), default="")
    enabled: Mapped[bool] = mapped_column(default=True)
    # Subscribed events as JSON array, e.g. ["plan_done","defect_assigned"]
    events: Mapped[str] = mapped_column(String(500), default="[]")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class NotificationLog(Base):
    """Audit log for sent notifications (success/failure/retry tracking)."""
    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(default=0, index=True)
    project_id: Mapped[int] = mapped_column(default=0)
    event: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(10), default="sent")  # sent / failed / retrying
    error: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
