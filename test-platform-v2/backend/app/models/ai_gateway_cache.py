"""Persistent exact-response cache for the local-first AI gateway."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AiResponseCache(Base, TimestampMixin):
    """One exact AI request/response pair, scoped to one project.

    Only hashes and response summaries are persisted. API keys, authorization
    headers, raw prompts and chain-of-thought never enter this table.
    """

    __tablename__ = "ai_response_cache"
    __table_args__ = (
        UniqueConstraint("cache_key", name="uq_ai_response_cache_cache_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    namespace: Mapped[str] = mapped_column(String(128), default="", index=True)
    cache_key: Mapped[str] = mapped_column(String(64), default="", index=True)
    provider_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    provider_type: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    input_hash: Mapped[str] = mapped_column(String(64), default="")
    response_json: Mapped[str] = mapped_column(Text, default="{}")
    usage_json: Mapped[str] = mapped_column(Text, default="{}")
    finish_reason: Mapped[str] = mapped_column(String(32), default="unknown")
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_hit_at: Mapped[datetime | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(default=None, index=True)
