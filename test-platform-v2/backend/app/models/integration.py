"""IntegrationConfig model — per-project external system connection (Jira / TAPD)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class IntegrationConfig(Base):
    __tablename__ = "integration_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    provider_type: Mapped[str] = mapped_column(String(20), default="jira")  # "jira" | "tapd"
    base_url: Mapped[str] = mapped_column(String(500), default="")
    auth_json: Mapped[str] = mapped_column(Text, default="")  # encrypted via cipher.encrypt_value
    field_mapping: Mapped[str] = mapped_column(Text, default="{}")  # JSON: custom severity/status mapping
    sync_direction: Mapped[str] = mapped_column(String(20), default="bidirectional")
    # bidirectional | push_only | pull_only
    sync_interval_minutes: Mapped[int] = mapped_column(default=0)  # 0 = auto-sync disabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
