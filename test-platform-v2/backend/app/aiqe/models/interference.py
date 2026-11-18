"""AUD-019：干扰观测（InterferenceObservation）与 TriageCase 生命周期。

- Detector 只产生 Observation（detector_key/窗口/signal/evidence），**不得修改 Run Outcome**；
- TriageCase 走固定生命周期：
  ``DETECTED → EVIDENCE_COLLECTED → HYPOTHESES_READY → EXPERIMENT_PROPOSED →
  EXPERIMENT_RUNNING → ATTRIBUTED | UNKNOWN | NEEDS_HUMAN``。
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class InterferenceObservation(Base):
    __tablename__ = "aiqe_interference_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("node_runs.id", ondelete="SET NULL"), nullable=True
    )
    detector_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    detector_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signal_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    evidence_refs_json: Mapped[list | None] = mapped_column(JSON, default=None)
    recommended_experiment: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_aiqe_interference_run_time", "project_id", "run_id", "observed_at"),
    )


class TriageCase(Base):
    __tablename__ = "aiqe_triage_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DETECTED", index=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attribution_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
