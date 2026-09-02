"""VersionTaskPlanItem — 版本验收任务的 AI 生成验收方案条目（B7）。

方案条目 = AI 生成的功能/接口/自动化场景，人工在审核面板逐条
采纳 / 修改 / 删除 / 追问；含置信度与待确认问题。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin
from app.models.version_task import VersionTask


class VersionTaskPlanItem(Base, TimestampMixin):
    __tablename__ = "version_task_plan_item"
    __table_args__ = (Index("ix_vt_plan_task_status", "task_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("version_task.id", ondelete="CASCADE"), index=True)
    # functional | api | scenario | check （功能 / 接口 / 自动化 / 核对点）
    item_type: Mapped[str] = mapped_column(String(30), default="functional", index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # 置信度 0-100（AI 生成）
    confidence: Mapped[int] = mapped_column(default=0, index=True)
    # draft | pending | adopted | modified | removed | asked（人工审核状态）
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    question: Mapped[str] = mapped_column(Text, default="")  # 待确认问题
    answer: Mapped[str] = mapped_column(Text, default="")  # 追问答复/备注
    order_index: Mapped[int] = mapped_column(default=0)

    task: Mapped[VersionTask] = relationship(back_populates="plan_items")
