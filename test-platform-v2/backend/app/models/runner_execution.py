"""内网执行器任务模型 — 平台派发内网 API 执行任务给 runner，runner 回传结果。

Batch 206 / C-内网执行器：平台服务器（公网）不可直达纯内网 API，
internal 环境 + execution_mode=runner 时创建本任务，由内网执行器（runner_key）认领执行。
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class RunnerExecutionTask(Base, TimestampMixin):
    __tablename__ = "runner_execution_task"
    __table_args__ = (
        Index("ix_runner_task_pending", "status", "runner_key", "locked_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True, default=0)
    environment_id: Mapped[int] = mapped_column(index=True)
    task_id: Mapped[str] = mapped_column(index=True, default="")     # 平台侧 execution_id
    runner_key: Mapped[str] = mapped_column(index=True, default="")  # 负责执行器；空=任意 runner
    request: Mapped[str] = mapped_column(Text, default="{}")          # {method,url,headers,body,query_params}
    assertions: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(default="pending", index=True)  # pending/claimed/done/failed
    result: Mapped[str] = mapped_column(Text, default="{}")            # runner 回传执行结果
    error_message: Mapped[str] = mapped_column(Text, default="")
    locked_at: Mapped[datetime | None] = mapped_column(default=None)
    locked_by: Mapped[str] = mapped_column(default="")
    claimed_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
