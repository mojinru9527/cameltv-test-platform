"""AI 生成用例审查状态模型 — 持久化审查队列，替代一次性 AiResultModal。

每个审查记录对应一条 AI 生成的候选用例。支持 approved/rejected/edited 三种状态。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RequirementReview(Base):
    __tablename__ = "requirement_review"

    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_document.id"), index=True
    )
    case_index: Mapped[int] = mapped_column(default=0)       # AI 生成用例的 index
    case_type: Mapped[str] = mapped_column(default="func")   # func / api
    status: Mapped[str] = mapped_column(default="pending")   # pending / approved / rejected / edited
    edited_data: Mapped[str] = mapped_column(default="{}")   # JSON: 编辑后的用例字段（仅 status=edited）
    reviewer_id: Mapped[int] = mapped_column(default=0)
    reviewed_at: Mapped[datetime] = mapped_column(default=datetime.now)
