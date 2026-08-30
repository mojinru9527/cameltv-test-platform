"""AITDE V3.8 ai-closed-loop repository (thin data access).

Keeps the router/service layers ORM-free per the route-layer ban convention.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.ai_closed_loop.models import (
    AiSuggestion,
    FailureHypothesis,
    FlakyCluster,
    FlakySignal,
    HumanFeedback,
    ModelEvaluationRun,
    ScenarioGapCandidate,
    StrategyPerformance,
)


# ── FailureHypothesis (V38-002/003) ──
def create_failure_hypothesis(db: Session, values: dict) -> FailureHypothesis:
    row = FailureHypothesis(**values)
    db.add(row)
    db.flush()
    return row


def list_hypotheses_for_run(db: Session, run_id: int) -> list[FailureHypothesis]:
    stmt = (
        select(FailureHypothesis)
        .where(FailureHypothesis.run_id == run_id)
        .order_by(FailureHypothesis.id)
    )
    return list(db.execute(stmt).scalars())


def get_failure_hypothesis(db: Session, hypothesis_id: int) -> FailureHypothesis | None:
    return db.get(FailureHypothesis, hypothesis_id)


# ── FlakySignal / FlakyCluster (V38-006/007) ──
def create_flaky_signal(db: Session, values: dict) -> FlakySignal:
    row = FlakySignal(**values)
    db.add(row)
    db.flush()
    return row


def list_flaky_signals_for_adapter(
    db: Session, scenario_adapter_id: int
) -> list[FlakySignal]:
    stmt = (
        select(FlakySignal)
        .where(FlakySignal.scenario_adapter_id == scenario_adapter_id)
        .order_by(FlakySignal.id)
    )
    return list(db.execute(stmt).scalars())


def create_flaky_cluster(db: Session, values: dict) -> FlakyCluster:
    row = FlakyCluster(**values)
    db.add(row)
    db.flush()
    return row


def get_flaky_cluster(db: Session, cluster_id: int) -> FlakyCluster | None:
    return db.get(FlakyCluster, cluster_id)


def list_flaky_clusters(
    db: Session, scenario_adapter_id: int | None = None
) -> list[FlakyCluster]:
    stmt = select(FlakyCluster).order_by(FlakyCluster.id)
    if scenario_adapter_id is not None:
        stmt = stmt.where(FlakyCluster.scenario_adapter_id == scenario_adapter_id)
    return list(db.execute(stmt).scalars())


def update_flaky_cluster(db: Session, row: FlakyCluster, values: dict) -> FlakyCluster:
    for key, value in values.items():
        setattr(row, key, value)
    db.flush()
    return row


# ── AiSuggestion (V38-011) ──
def create_suggestion(db: Session, values: dict) -> AiSuggestion:
    row = AiSuggestion(**values)
    db.add(row)
    db.flush()
    return row


def list_suggestions(
    db: Session, project_id: int, status: str | None = None
) -> list[AiSuggestion]:
    stmt = (
        select(AiSuggestion)
        .where(AiSuggestion.project_id == project_id)
        .order_by(AiSuggestion.id.desc())
    )
    if status is not None:
        stmt = stmt.where(AiSuggestion.status == status)
    return list(db.execute(stmt).scalars())


def get_suggestion(db: Session, suggestion_id: int) -> AiSuggestion | None:
    return db.get(AiSuggestion, suggestion_id)


def update_suggestion(
    db: Session, row: AiSuggestion, values: dict
) -> AiSuggestion:
    for key, value in values.items():
        setattr(row, key, value)
    db.flush()
    return row


# ── HumanFeedback (V38-012) ──
def create_feedback(db: Session, values: dict) -> HumanFeedback:
    row = HumanFeedback(**values)
    db.add(row)
    db.flush()
    return row


def list_feedback(
    db: Session, project_id: int, target_type: str | None = None
) -> list[HumanFeedback]:
    stmt = (
        select(HumanFeedback)
        .where(HumanFeedback.project_id == project_id)
        .order_by(HumanFeedback.id.desc())
    )
    if target_type is not None:
        stmt = stmt.where(HumanFeedback.target_type == target_type)
    return list(db.execute(stmt).scalars())


# ── StrategyPerformance (V38-008) ──
def get_strategy_performance(
    db: Session,
    project_id: int,
    strategy_type: str,
    strategy_key: str,
    context_hash: str,
) -> StrategyPerformance | None:
    stmt = select(StrategyPerformance).where(
        StrategyPerformance.project_id == project_id,
        StrategyPerformance.strategy_type == strategy_type,
        StrategyPerformance.strategy_key == strategy_key,
        StrategyPerformance.context_hash == context_hash,
    )
    return db.execute(stmt.limit(1)).scalars().first()


def create_strategy_performance(db: Session, values: dict) -> StrategyPerformance:
    row = StrategyPerformance(**values)
    db.add(row)
    db.flush()
    return row


def list_strategy_performance(
    db: Session, project_id: int
) -> list[StrategyPerformance]:
    stmt = (
        select(StrategyPerformance)
        .where(StrategyPerformance.project_id == project_id)
        .order_by(StrategyPerformance.id)
    )
    return list(db.execute(stmt).scalars())


# ── ScenarioGapCandidate (V38-010) ──
def create_gap_candidate(db: Session, values: dict) -> ScenarioGapCandidate:
    row = ScenarioGapCandidate(**values)
    db.add(row)
    db.flush()
    return row


def list_gap_candidates(db: Session, mission_id: int) -> list[ScenarioGapCandidate]:
    stmt = (
        select(ScenarioGapCandidate)
        .where(ScenarioGapCandidate.mission_id == mission_id)
        .order_by(ScenarioGapCandidate.id)
    )
    return list(db.execute(stmt).scalars())


def get_gap_candidate(db: Session, gap_id: int) -> ScenarioGapCandidate | None:
    return db.get(ScenarioGapCandidate, gap_id)


def update_gap_candidate(
    db: Session, row: ScenarioGapCandidate, values: dict
) -> ScenarioGapCandidate:
    for key, value in values.items():
        setattr(row, key, value)
    db.flush()
    return row


# ── ModelEvaluationRun (V38-013) ──
def create_model_evaluation(db: Session, values: dict) -> ModelEvaluationRun:
    row = ModelEvaluationRun(**values)
    db.add(row)
    db.flush()
    return row


def get_model_evaluation(db: Session, evaluation_id: int) -> ModelEvaluationRun | None:
    return db.get(ModelEvaluationRun, evaluation_id)


def list_model_evaluations(db: Session) -> list[ModelEvaluationRun]:
    stmt = select(ModelEvaluationRun).order_by(ModelEvaluationRun.id.desc())
    return list(db.execute(stmt).scalars())


def update_model_evaluation(
    db: Session, row: ModelEvaluationRun, values: dict
) -> ModelEvaluationRun:
    for key, value in values.items():
        setattr(row, key, value)
    db.flush()
    return row
