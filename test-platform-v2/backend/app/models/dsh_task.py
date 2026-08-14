"""DSH 任务执行模块 ORM 模型 — Batch 172。

用户提交自然语言任务，平台通过 DeepSeek Harness 后台执行，状态与输出落库可追溯。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DshTask(Base):
    __tablename__ = "dsh_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    task: Mapped[str] = mapped_column(Text, default="")          # 任务文本
    status: Mapped[str] = mapped_column(default="pending", index=True)  # pending/running/success/failed/cancelled
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    output_text: Mapped[str] = mapped_column(Text, default="")   # harness 最终输出
    session_dir: Mapped[str] = mapped_column(default="")
    error: Mapped[str] = mapped_column(Text, default="")
    operator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    # Batch 181：统一认领锁（P2-06）；此前 started_at 兼作锁字段，现语义分离
    locked_at: Mapped[datetime | None] = mapped_column(default=None)
    locked_by: Mapped[str] = mapped_column(default="")
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
