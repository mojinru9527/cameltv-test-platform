"""Scope / Ambiguity / Intent models (V30-030, M2)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import (
    AmbiguityStatus,
    ReviewStatus,
    RiskLevel,
    ScopeDecision,
    ScopeType,
    TestDepth,
)


class ScopeItem(Base, TimestampMixin):
    __tablename__ = "scope_items"
    __table_args__ = (
        UniqueConstraint("mission_id", "scope_key", name="uq_scope_mission_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    scope_key: Mapped[str] = mapped_column(String(128), default="")
    scope_type: Mapped[str] = mapped_column(String(32), default=ScopeType.FEATURE.value)
    name: Mapped[str] = mapped_column(String(255), default="")
    decision: Mapped[str] = mapped_column(
        String(16), default=ScopeDecision.INCLUDE.value
    )
    test_depth: Mapped[str] = mapped_column(String(16), default=TestDepth.FULL.value)
    risk_level: Mapped[str] = mapped_column(String(4), default=RiskLevel.P2.value)
    reason: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(
        String(16), default=ReviewStatus.PROPOSED.value, index=True
    )
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)


class Ambiguity(Base, TimestampMixin):
    __tablename__ = "ambiguities"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    ambiguity_key: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(4), default=RiskLevel.P2.value)
    status: Mapped[str] = mapped_column(
        String(24), default=AmbiguityStatus.OPEN.value, index=True
    )
    candidate_options_json: Mapped[str] = mapped_column(Text, default="[]")
    selected_option_json: Mapped[str] = mapped_column(Text, default="{}")
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    resolution_note: Mapped[str] = mapped_column(Text, default="")
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    resolved_by: Mapped[int | None] = mapped_column(Integer, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)


class TestIntent(Base, TimestampMixin):
    __tablename__ = "test_intents"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    intent_key: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    business_goal: Mapped[str] = mapped_column(Text, default="")
    required_outcomes_json: Mapped[str] = mapped_column(Text, default="[]")
    risk_level: Mapped[str] = mapped_column(String(4), default=RiskLevel.P2.value)
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    review_status: Mapped[str] = mapped_column(
        String(16), default=ReviewStatus.PROPOSED.value
    )
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    reviewed_by: Mapped[int | None] = mapped_column(Integer, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
