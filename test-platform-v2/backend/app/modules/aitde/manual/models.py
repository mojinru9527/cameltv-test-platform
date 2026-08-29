"""AITDE V3.3 Manual execution models (V33-008)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.common.enums import ManualStepStatus


class ManualExecutionSession(Base):
    __tablename__ = "manual_execution_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    browser_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tester_id: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    started_at: Mapped[datetime] = mapped_column(default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ManualExecutionStep(Base):
    __tablename__ = "manual_execution_steps"
    __table_args__ = (
        UniqueConstraint("manual_session_id", "sequence", name="uq_manual_step_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    manual_session_id: Mapped[int] = mapped_column(Integer, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    step_key: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(
        String(16), default=ManualStepStatus.PENDING.value, index=True
    )
    tester_note: Mapped[str] = mapped_column(Text, default="")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
