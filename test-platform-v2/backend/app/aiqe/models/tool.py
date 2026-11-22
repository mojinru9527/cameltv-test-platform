"""V16-019：AIQE Agent 工具执行审计模型。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ToolExecutionAudit(Base):
    __tablename__ = "aiqe_tool_execution_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(16), nullable=False, default="", index=True)
    task_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    tool_version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    side_effect_level: Mapped[str] = mapped_column(String(16), nullable=False, default="READ")
    decision: Mapped[str] = mapped_column(String(16), nullable=False, default="ALLOW")
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    args_hash: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    args_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence_refs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_aiqe_tool_audits_project_tool", "project_id", "tool_name"),
        Index("ix_aiqe_tool_audits_task", "project_id", "task_id"),
    )
