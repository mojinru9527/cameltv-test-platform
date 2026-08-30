"""AITDE V3.8 AI QA Closed Loop models (V38).

Data model for Failure Evidence Pack → Hypothesis → Healing → Flaky → Strategy →
Gap → Suggestion → Feedback → Model Evaluation → Auto-Retry vocabulary per the
V3.8 plan §2. Created by the M38 alembic migration. String-valued enums so they
stay stable across SQLite/PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.aitde.common.enums import (
    FailureClassification,
    FailureHypothesisStatus,
    FlakyClassification,
    FlakySignalType,
    GapCandidateStatus,
    ModelEvaluationStatus,
    SuggestionStatus,
    SuggestionType,
)


class FailureHypothesis(Base):
    """V38-002: an AI failure hypothesis over a formal run outcome.

    AI never writes the Outcome; it only produces a structured hypothesis and
    suggested checks. ``status`` moves GENERATED → REVIEWED → CONFIRMED/REJECTED.
    """

    __tablename__ = "failure_hypotheses"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    hypothesis_type: Mapped[str] = mapped_column(
        String(48), default=FailureClassification.UNKNOWN.value, index=True
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    suggested_checks_json: Mapped[str] = mapped_column(Text, default="[]")
    model_ref: Mapped[str | None] = mapped_column(String(255), default=None)
    prompt_version: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[str] = mapped_column(
        String(16), default=FailureHypothesisStatus.GENERATED.value, index=True
    )
    reviewed_by: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class FlakySignal(Base):
    """V38-006: one flaky signal derived from a run/step signature."""

    __tablename__ = "flaky_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_adapter_id: Mapped[int] = mapped_column(Integer, index=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    signal_type: Mapped[str] = mapped_column(
        String(32), default=FlakySignalType.INTERMITTENT_ERROR.value, index=True
    )
    signature: Mapped[str] = mapped_column(String(255), default="", index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class FlakyCluster(Base):
    """V38-007: an aggregated flaky cluster keyed by adapter + signature."""

    __tablename__ = "flaky_clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_adapter_id: Mapped[int] = mapped_column(Integer, index=True)
    cluster_key: Mapped[str] = mapped_column(String(255), default="", index=True)
    classification: Mapped[str] = mapped_column(
        String(16), default=FlakyClassification.UNCLASSIFIED.value, index=True
    )
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class AiSuggestion(Base):
    """V38-011: an AI suggestion in a Tester-controlled inbox."""

    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    suggestion_type: Mapped[str] = mapped_column(
        String(32), default=SuggestionType.RISK.value, index=True
    )
    target_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    target_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(16), default=SuggestionStatus.OPEN.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class HumanFeedback(Base):
    """V38-012: append-only Tester correction / confirmation / rejection log."""

    __tablename__ = "human_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    mission_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    target_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    target_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    feedback_type: Mapped[str] = mapped_column(
        String(16), default="CORRECTION", index=True
    )
    before_json: Mapped[str | None] = mapped_column(Text, default=None)
    after_json: Mapped[str | None] = mapped_column(Text, default=None)
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class StrategyPerformance(Base):
    """V38-008: strategy performance metrics (project-scoped)."""

    __tablename__ = "strategy_performance"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    strategy_type: Mapped[str] = mapped_column(String(32), default="DATA", index=True)
    strategy_key: Mapped[str] = mapped_column(String(128), default="", index=True)
    context_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    median_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    failure_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ScenarioGapCandidate(Base):
    """V38-010: a proposed Scenario gap (proposal only — never a formal Expected)."""

    __tablename__ = "scenario_gap_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(Integer, index=True)
    gap_type: Mapped[str] = mapped_column(
        String(32), default="PROD_NEW_STATE", index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_refs_json: Mapped[str] = mapped_column(Text, default="[]")
    risk_level: Mapped[str] = mapped_column(String(4), default="P2", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(16), default=GapCandidateStatus.OPEN.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)


class ModelEvaluationRun(Base):
    """V38-013: a golden model/prompt evaluation run."""

    __tablename__ = "model_evaluation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_suite: Mapped[str] = mapped_column(String(128), default="", index=True)
    model_ref: Mapped[str] = mapped_column(String(255), default="", index=True)
    prompt_versions_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(
        String(16), default=ModelEvaluationStatus.PENDING.value, index=True
    )
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    artifact_uri: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now, index=True)
