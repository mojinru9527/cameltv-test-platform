"""M5 / TA-030：Learning Curator 模型（learning_candidates / bug_patterns）。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LearningCandidate(Base):
    __tablename__ = "learning_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="bug")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    benchmark_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # ── V16-010：服务端 gate 评估快照与审批/发布字段（不可由调用方自报）──
    benchmark_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    baseline_version: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    gate_policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    gate_decision: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    gate_reasons_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evaluation_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rule_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duplicate_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class BugPattern(Base):
    __tablename__ = "bug_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pattern_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    source_candidate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
