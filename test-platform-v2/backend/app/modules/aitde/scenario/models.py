"""Scenario / Oracle models (V30-060/V30-061, M3)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin
from app.modules.aitde.common.enums import (
    ReviewStatus,
    ScenarioReviewStatus,
    RiskLevel,
)


class TestScenario(Base, TimestampMixin):
    __tablename__ = "test_scenarios"
    __table_args__ = (
        UniqueConstraint("mission_id", "scenario_key", name="uq_scenario_mission_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_key: Mapped[str] = mapped_column(String(128), default="")
    current_version_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")


class TestScenarioVersion(Base, TimestampMixin):
    __tablename__ = "test_scenario_versions"
    __table_args__ = (
        UniqueConstraint("scenario_id", "version_no", name="uq_scenario_version_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(Integer, index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    contract_version_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    business_goal: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(4), default=RiskLevel.P2.value)
    risk_level: Mapped[str] = mapped_column(String(4), default=RiskLevel.P2.value)
    given_model_json: Mapped[str] = mapped_column(Text, default="{}")
    when_model_json: Mapped[str] = mapped_column(Text, default="{}")
    expected_state_json: Mapped[str] = mapped_column(Text, default="{}")
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    review_status: Mapped[str] = mapped_column(
        String(16), default=ScenarioReviewStatus.PROPOSED.value, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    approved_by: Mapped[int | None] = mapped_column(Integer, default=None)
    approved_at: Mapped[datetime | None] = mapped_column(default=None)
    supersedes_version_id: Mapped[int | None] = mapped_column(Integer, default=None)


class TestOracle(Base):
    __tablename__ = "test_oracles"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    oracle_key: Mapped[str] = mapped_column(String(128), default="")
    oracle_type: Mapped[str] = mapped_column(String(16), default="DB")
    target_json: Mapped[str] = mapped_column(Text, default="{}")
    operator: Mapped[str] = mapped_column(String(32), default="eq")
    expected_value_json: Mapped[str] = mapped_column(Text, default="{}")
    source_type: Mapped[str] = mapped_column(String(32), default="REQUIREMENT_EXPLICIT")
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    review_status: Mapped[str] = mapped_column(
        String(16), default=ReviewStatus.PROPOSED.value
    )
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
