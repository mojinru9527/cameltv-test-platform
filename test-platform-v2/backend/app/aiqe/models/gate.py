"""PR #595 后 v1.4：质量门禁不可变快照。

门禁结果只能由服务端从持久化事实计算；每次重新验收生成新行，
历史行不允许更新（append-only），避免新 Run 回写改变历史结论。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class QualityGateSnapshot(Base):
    __tablename__ = "aiqe_quality_gate_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False
    )
    version_task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("version_task.id", ondelete="SET NULL"), nullable=True
    )
    gate_status: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.4")
    build_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    environment_ref: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    contract_checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    p0_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p0_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p0_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p0_blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reasons_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    computed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_aiqe_gate_project_computed", "project_id", "computed_at"),
        Index("ix_aiqe_gate_task_computed", "version_task_id", "computed_at"),
    )
