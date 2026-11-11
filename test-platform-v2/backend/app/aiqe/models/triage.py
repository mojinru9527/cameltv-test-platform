"""M3 / TA-025：反事实重放实验记录（triage_experiments）。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TriageExperiment(Base):
    __tablename__ = "triage_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    triage_case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    hypothesis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    experiment_key: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    changed_variable: Mapped[str] = mapped_column(String(128), nullable=False)
    changed_value: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("execution_profiles.id", ondelete="SET NULL"), nullable=True
    )
    verification_run_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
