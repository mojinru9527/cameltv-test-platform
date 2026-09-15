"""Canonical external AI job and local agent registry."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AiJob(Base, TimestampMixin):
    __tablename__ = "ai_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    input_ref: Mapped[str] = mapped_column(String(512), default="")
    capability: Mapped[str] = mapped_column(String(128), default="", index=True)
    model_hint: Mapped[str] = mapped_column(String(128), default="")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=900)
    agent_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    error_message: Mapped[str] = mapped_column(Text, default="")
    locked_at: Mapped[datetime | None] = mapped_column(default=None)
    heartbeat_at: Mapped[datetime | None] = mapped_column(default=None)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class AiAgent(Base, TimestampMixin):
    __tablename__ = "ai_agents"
    __table_args__ = (UniqueConstraint("agent_id", name="uq_ai_agent_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    project_scope: Mapped[int] = mapped_column(Integer, default=0, index=True)
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="online", index=True)
    last_health_at: Mapped[datetime | None] = mapped_column(default=None)


class AiResult(Base, TimestampMixin):
    __tablename__ = "ai_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
