"""Persistent comparison facts for local-model shadow evaluation."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AiShadowRun(Base, TimestampMixin):
    """One primary-vs-local comparison. Full prompts and outputs are not stored."""

    __tablename__ = "ai_shadow_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    namespace: Mapped[str] = mapped_column(String(128), default="", index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    input_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    json_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    primary_provider: Mapped[str] = mapped_column(String(64), default="")
    primary_model: Mapped[str] = mapped_column(String(128), default="")
    shadow_provider: Mapped[str] = mapped_column(String(64), default="")
    shadow_model: Mapped[str] = mapped_column(String(128), default="")
    primary_content_hash: Mapped[str] = mapped_column(String(64), default="")
    shadow_content_hash: Mapped[str] = mapped_column(String(64), default="")
    primary_json_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    shadow_json_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    exact_match: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    shadow_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    length_delta: Mapped[int] = mapped_column(Integer, default=0)
    primary_usage_json: Mapped[str] = mapped_column(Text, default="{}")
    shadow_usage_json: Mapped[str] = mapped_column(Text, default="{}")
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(String(500), default="")
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
