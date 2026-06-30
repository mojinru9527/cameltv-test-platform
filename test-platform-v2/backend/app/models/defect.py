"""Defect ORM model + transition history."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Defect(Base):
    __tablename__ = "defect"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(default=0, index=True)
    defect_id: Mapped[str] = mapped_column(String(50), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="P2")       # P0/P1/P2/P3
    status: Mapped[str] = mapped_column(String(20), default="open")
    # Statuses: open → confirmed → fixing → pending_review → closed / rejected
    #   rejected / closed → open (reopen)
    case_id: Mapped[Optional[int]] = mapped_column(default=None, index=True)
    execution_id: Mapped[Optional[int]] = mapped_column(default=None)
    assignee_id: Mapped[int] = mapped_column(default=0, index=True)
    external_id: Mapped[str] = mapped_column(String(100), default="")     # 禅道/Jira ID
    external_url: Mapped[str] = mapped_column(String(500), default="")    # 外部链接
    creator_id: Mapped[int] = mapped_column(default=0)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    transitions: Mapped[list["DefectTransition"]] = relationship(
        back_populates="defect", order_by="DefectTransition.created_at.asc()",
    )


class DefectTransition(Base):
    """Audit trail for defect status transitions."""
    __tablename__ = "defect_transition"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect.id"), index=True)
    from_status: Mapped[str] = mapped_column(String(20), default="")
    to_status: Mapped[str] = mapped_column(String(20), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    operator_id: Mapped[int] = mapped_column(default=0)
    operator_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    # Relationship back
    defect: Mapped[Defect] = relationship(back_populates="transitions")


class DefectComment(Base):
    """User comments on defects."""
    __tablename__ = "defect_comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defect.id"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    author_id: Mapped[int] = mapped_column(default=0)
    author_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
