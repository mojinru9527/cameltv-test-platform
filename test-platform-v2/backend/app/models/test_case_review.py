"""TestCaseReviewTransition — 用例评审流转审计轨迹。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class TestCaseReviewTransition(Base):
    __tablename__ = "test_case_review_transition"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("test_case.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str] = mapped_column(String(20), default="")
    to_status: Mapped[str] = mapped_column(String(20), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    reviewer_id: Mapped[int] = mapped_column(default=0)
    reviewer_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    case: Mapped["TestCase"] = relationship(back_populates="review_transitions")  # noqa: F821
