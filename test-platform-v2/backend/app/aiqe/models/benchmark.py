"""AUD-018：A6 Benchmark 数据集 / 样本 / 执行记录模型。

指标必须由后端从真实执行/标注结果计算（v1.5 §03 AUD-018），
``BenchmarkRun.metrics_json`` 是唯一可信指标来源，API 不接受 Agent 自报数值。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BenchmarkDataset(Base):
    __tablename__ = "aiqe_benchmark_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=True, index=True
    )
    dataset_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    task_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    content_hash: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gate_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT", index=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint(
            "dataset_key", "revision", name="uq_aiqe_benchmark_dataset_key_revision"
        ),
    )


class BenchmarkSample(Base):
    __tablename__ = "aiqe_benchmark_samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("aiqe_benchmark_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_id: Mapped[str] = mapped_column(String(120), nullable=False)
    task_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    input_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    frozen_context_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    expected_schema_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    golden_labels_json: Mapped[list | None] = mapped_column(JSON, default=None)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    labeler: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    reviewer: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("dataset_id", "sample_id", name="uq_aiqe_benchmark_sample_dataset"),
    )


class BenchmarkRun(Base):
    __tablename__ = "aiqe_benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("aiqe_benchmark_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_key: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    agent_version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    prompt_hash: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    model_provider: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    model_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="RUNNING")
    result_status: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    per_sample_json: Mapped[list | None] = mapped_column(JSON, default=None)
    token_usage_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
