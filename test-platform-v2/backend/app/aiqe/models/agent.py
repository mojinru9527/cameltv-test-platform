"""M3 / TA-019 + AUD-013：Agent 执行记录模型（13 号 §4.19）。

AUD-013 起每条执行记录都必须可追溯：Agent 版本、Prompt 版本、模型 provider/name、
输入/输出 hash、token 用量、source refs、tool calls、warnings、needs_human。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    agent_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    model: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    input_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # ── AUD-013 ──
    agent_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    model_provider: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    model_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    input_hash: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    output_hash: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    token_usage_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tool_calls_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    warnings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    needs_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    task_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    parent_task_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
