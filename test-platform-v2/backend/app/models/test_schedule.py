"""TestSchedule + TestScheduleRun ORM models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.test_plan import TestPlan


class TestSchedule(Base):
    __tablename__ = "test_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    plan_id: Mapped[int] = mapped_column(ForeignKey("test_plan.id"), index=True)
    cron_expression: Mapped[str] = mapped_column(String(100), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    creator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    plan: Mapped["TestPlan"] = relationship("TestPlan")
    runs: Mapped[list["TestScheduleRun"]] = relationship(
        "TestScheduleRun", back_populates="schedule",
        cascade="all, delete-orphan", order_by="TestScheduleRun.started_at.desc()",
    )


class TestScheduleRun(Base):
    __tablename__ = "test_schedule_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("test_schedule.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    result: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    schedule: Mapped["TestSchedule"] = relationship("TestSchedule", back_populates="runs")
