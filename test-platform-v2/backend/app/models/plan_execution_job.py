"""Durable dispatch record for an asynchronous test-plan execution."""
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.task_queue import utcnow


class PlanExecutionJob(Base):
    __tablename__ = 'plan_execution_job'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    plan_id: Mapped[int] = mapped_column(index=True)
    creator_id: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    request_json: Mapped[str] = mapped_column(Text, default='{}')
    result_json: Mapped[str] = mapped_column(Text, default='{}')
    error_message: Mapped[str] = mapped_column(Text, default='')
    locked_by: Mapped[str] = mapped_column(String(64), default='')
    locked_at: Mapped[datetime | None] = mapped_column(default=None)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
