"""AI 异步任务（C117-2 DB 队列，多 worker 可消费）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class AiTask(Base, TimestampMixin):
    __tablename__ = "ai_task"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(20), default="", index=True)  # extract | generate
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    document_id: Mapped[int] = mapped_column(default=0, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|running|done|failed
    progress: Mapped[int] = mapped_column(default=0)
    result_json: Mapped[str] = mapped_column(Text, default="null")
    error: Mapped[str] = mapped_column(Text, default="")
    locked_at: Mapped[datetime | None] = mapped_column(default=None)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
