"""VersionKnowledgeRecord — 版本知识记录（B11）。

版本任务放行后自动沉淀「这版怎么测的」，供下一版本建任务时复用。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class VersionKnowledgeRecord(Base, TimestampMixin):
    __tablename__ = "version_knowledge_record"
    __table_args__ = (UniqueConstraint("task_id", name="uq_version_knowledge_task"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("version_task.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(80), default="", index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    coverage: Mapped[str] = mapped_column(Text, default="{}")
    verdict: Mapped[str] = mapped_column(String(20), default="", index=True)
    risk: Mapped[str] = mapped_column(Text, default="[]")
    plan_summary: Mapped[str] = mapped_column(Text, default="[]")  # 采纳的方案条目
    defect_count: Mapped[int] = mapped_column(default=0)
