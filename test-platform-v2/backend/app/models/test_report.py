"""TestReport ORM model."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TestReport(Base):
    __tablename__ = "test_report"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    report_id: Mapped[str] = mapped_column(String(50), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    plan_id: Mapped[int] = mapped_column(ForeignKey("test_plan.id"), index=True)
    content: Mapped[str] = mapped_column(Text, default="{}")
    template_id: Mapped[int | None] = mapped_column(ForeignKey("report_template.id"), default=None, nullable=True)
    creator_id: Mapped[int] = mapped_column(default=0)
    gate_status: Mapped[str | None] = mapped_column(String(20), default=None, nullable=True)  # pass/fail/warn
    gate_details: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of detail strings
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
