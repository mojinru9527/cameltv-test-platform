"""M3 / TA-025 + AUD-004：反事实重放实验记录（triage_experiments）。

AUD-004 不变量（v1.5 §01 AUD-004）：

- 实验创建只落 Draft/Validated，**不允许**直接 completed；
- ``verification_run_id`` 必须指向真实存在的 ``test_runs`` 行，禁止用 ``uuid4()`` 占位；
- ``COMPLETED`` 只能由 ``sync_experiment_result()`` 在验证 Run 进入终态后写入；
- 单变量语义由 ``changed_dimension`` + ``snapshot_diff_json`` 证明（E1–E6 各只允许一个维度）。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TriageExperiment(Base):
    __tablename__ = "triage_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    triage_case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    hypothesis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    experiment_key: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    changed_variable: Mapped[str] = mapped_column(String(128), nullable=False)
    changed_value: Mapped[str] = mapped_column(String(255), nullable=False)
    # 规范字段名（v1.5 §06 2.5）：唯一变更维度，与 E1–E6 矩阵一一对应。
    changed_dimension: Mapped[str | None] = mapped_column(String(64), nullable=True)
    baseline_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("execution_profiles.id", ondelete="SET NULL"), nullable=True
    )
    verification_run_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    baseline_snapshot_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_snapshot_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    snapshot_diff_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    experiment_result: Mapped[str | None] = mapped_column(String(24), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
