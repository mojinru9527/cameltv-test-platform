"""AITDE V3.7 Impact Analysis + Smart Regression models (V37).

Data model for Lineage Edge → ChangeSet/Item → Impact Run/Result → Regression
Selection (plan §§2-6). Created by the M37 alembic migration. String-valued
enums so they stay stable across SQLite/PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.common.enums import (
    ChangeItemKind,
    ChangeSetStatus,
    ChangeSetType,
    ImpactDecision,
    ImpactRunStatus,
    SelectionDecision,
    SelectionType,
)


class LineageEdge(Base):
    """V37-001: a directed edge tying two lineage nodes across the AITDE graph.

    ``from_node`` -> ``to_node``; ``edge_type`` carries the relationship. Core FK
    relations remain the source of truth; ``lineage_edges`` records cross-domain
    paths and explanations. Edges are deduplicated by the unique constraint.
    """

    __tablename__ = "lineage_edges"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "from_type",
            "from_id",
            "to_type",
            "to_id",
            "edge_type",
            name="uq_lineage_edge",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    from_type: Mapped[str] = mapped_column(String(32), index=True)
    from_id: Mapped[int] = mapped_column(Integer, index=True)
    to_type: Mapped[str] = mapped_column(String(32), index=True)
    to_id: Mapped[int] = mapped_column(Integer, index=True)
    edge_type: Mapped[str] = mapped_column(String(32), index=True)
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_by_type: Mapped[str] = mapped_column(String(16), default="SYSTEM")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ChangeSet(Base):
    """V37-003..007: a normalized batch of detected changes from one provider."""

    __tablename__ = "change_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    change_type: Mapped[str] = mapped_column(
        String(32), default=ChangeSetType.PRD.value, index=True
    )
    source_from_ref: Mapped[str | None] = mapped_column(Text, default=None)
    source_to_ref: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(
        String(16), default=ChangeSetStatus.DETECTED.value, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ChangeItem(Base):
    """V37-003..007: one normalized change inside a ChangeSet."""

    __tablename__ = "change_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_set_id: Mapped[int] = mapped_column(Integer, index=True)
    change_kind: Mapped[str] = mapped_column(
        String(16), default=ChangeItemKind.CHANGED.value, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    entity_key: Mapped[str] = mapped_column(String(255), default="", index=True)
    before_json: Mapped[str | None] = mapped_column(Text, default=None)
    after_json: Mapped[str | None] = mapped_column(Text, default=None)
    risk_hint: Mapped[str] = mapped_column(String(32), default="NONE", index=True)
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")


class ImpactAnalysisRun(Base):
    """V37-008: one deterministic impact-analysis execution over a ChangeSet."""

    __tablename__ = "impact_analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    change_set_id: Mapped[int] = mapped_column(Integer, index=True)
    algorithm_version: Mapped[str] = mapped_column(String(16), default="v1")
    status: Mapped[str] = mapped_column(
        String(16), default=ImpactRunStatus.PENDING.value, index=True
    )
    input_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class ImpactResult(Base):
    """V37-008: an impacted Scenario (by version) produced by an analysis run."""

    __tablename__ = "impact_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    impact_run_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(4), default="P2", index=True)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    path_json: Mapped[str] = mapped_column(Text, default="[]")
    decision: Mapped[str] = mapped_column(
        String(16), default=ImpactDecision.INCLUDE.value, index=True
    )


class RegressionSelection(Base):
    """V37-009/010: an immutable regression selection snapshot for a Mission."""

    __tablename__ = "regression_selections"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    impact_run_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    build_observation_id: Mapped[int | None] = mapped_column(
        Integer, default=None, index=True
    )
    selection_type: Mapped[str] = mapped_column(
        String(16), default=SelectionType.SMART.value, index=True
    )
    selected_json: Mapped[str] = mapped_column(Text, default="[]")
    excluded_json: Mapped[str] = mapped_column(Text, default="[]")
    fallback_reason: Mapped[str | None] = mapped_column(Text, default=None)
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class RegressionSelectionItem(Base):
    """V37-013: one scenario decision inside a RegressionSelection (audited)."""

    __tablename__ = "regression_selection_items"
    __table_args__ = (
        UniqueConstraint("selection_id", "scenario_version_id", name="uq_reg_sel_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    selection_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_id: Mapped[int] = mapped_column(Integer, index=True)
    scenario_version_id: Mapped[int] = mapped_column(Integer, index=True)
    decision: Mapped[str] = mapped_column(
        String(16), default=SelectionDecision.SELECTED.value, index=True
    )
    reason: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(32), default="SYSTEM")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
