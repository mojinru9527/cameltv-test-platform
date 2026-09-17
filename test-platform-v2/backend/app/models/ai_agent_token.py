"""Batch 248 — 本地 AI Agent 凭据（sha256 存哈希，明文仅注册时返回一次）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AiAgentToken(Base, TimestampMixin):
    __tablename__ = "ai_agent_token"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_prefix: Mapped[str] = mapped_column(String(12), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
