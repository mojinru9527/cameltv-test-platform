"""ReuseSuggestionEvent —— 复用建议的埋点（Batch 260 / B3-4）。

**为什么需要它**：B11/B12 已经能把"上一版怎么测的"在下版建任务时**自动带出**，
但没有任何地方记录"带出了什么、人工最后采纳了没有"。没有这条数据，
09 方案 §2.3 的「复用建议命中率 ≥50%」就只是一个无法计算的指标。

口径（与 B3-4 的 DoD 对齐）：
  - `suggested`：一次带出即一条（同一 task + suggestion_ref 只记一次）；
  - `adopted` / `rejected`：人工对该建议的决定；
  - 命中率 = `adopted / suggested`。

采用**追加式事件**（而非在原记录上改字段），便于审计与回溯"谁在什么时候改的主意"。
"""
from __future__ import annotations

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin

DECISIONS = frozenset({"suggested", "adopted", "rejected"})


class ReuseSuggestionEvent(Base, TimestampMixin):
    __tablename__ = "reuse_suggestion_event"
    __table_args__ = (
        UniqueConstraint(
            "task_id", "suggestion_ref", "decision", name="uq_reuse_suggestion_event"
        ),
        Index("ix_reuse_suggestion_project_task", "project_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    task_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    suggestion_ref: Mapped[str] = mapped_column(String(200), default="", index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    decision: Mapped[str] = mapped_column(String(20), default="suggested", index=True)
    decided_by: Mapped[int] = mapped_column(Integer, default=0)
