"""VersionTaskRun — 版本验收任务的执行运行记录（B8）。

一键运行任务后记录：进度、覆盖计数、证据（截图/请求/回放）、失败四分类（业务/脚本/数据/环境）。
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.version_task import VersionTask


class VersionTaskRun(Base, TimestampMixin):
    __tablename__ = "version_task_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("version_task.id", ondelete="CASCADE"), index=True)
    # pending | running | done | failed
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    progress: Mapped[int] = mapped_column(default=0)  # 0-100
    total: Mapped[int] = mapped_column(default=0)
    passed: Mapped[int] = mapped_column(default=0)
    failed: Mapped[int] = mapped_column(default=0)
    skipped: Mapped[int] = mapped_column(default=0)
    blocked: Mapped[int] = mapped_column(default=0)
    evidence: Mapped[str] = mapped_column(Text, default="[]")   # [{type,ref,url,ts}]
    failures: Mapped[str] = mapped_column(Text, default="[]")   # [{item_id,title,kind,evidence,message}]
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)

    task: Mapped[VersionTask] = relationship(back_populates="runs")
