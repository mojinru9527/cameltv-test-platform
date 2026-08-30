"""AITDE V3.7 smart-regression repository (thin data access).

Keeps the router/service layers ORM-free per the route-layer ban convention.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.smart_regression.models import (
    ChangeItem,
    ChangeSet,
    ImpactAnalysisRun,
    ImpactResult,
    LineageEdge,
    RegressionSelection,
    RegressionSelectionItem,
)


def list_lineage_edges(
    db: Session, project_id: int, mission_id: int | None = None
) -> list[LineageEdge]:
    stmt = select(LineageEdge).where(LineageEdge.project_id == project_id)
    if mission_id is not None:
        stmt = stmt.where(LineageEdge.mission_id == mission_id)
    return list(db.execute(stmt.order_by(LineageEdge.id)).scalars())


def get_edge(db: Session, edge_id: int) -> LineageEdge | None:
    return db.get(LineageEdge, edge_id)


def create_change_set(
    db: Session,
    project_id: int,
    mission_id: int,
    change_type: str,
    source_from_ref: str | None,
    source_to_ref: str | None,
    content_hash: str,
    status: str,
) -> ChangeSet:
    row = ChangeSet(
        project_id=project_id,
        mission_id=mission_id,
        change_type=change_type,
        source_from_ref=source_from_ref,
        source_to_ref=source_to_ref,
        content_hash=content_hash,
        status=status,
    )
    db.add(row)
    db.flush()
    return row


def get_change_set(db: Session, change_set_id: int) -> ChangeSet | None:
    return db.get(ChangeSet, change_set_id)


def list_change_items(db: Session, change_set_id: int) -> list[ChangeItem]:
    stmt = (
        select(ChangeItem)
        .where(ChangeItem.change_set_id == change_set_id)
        .order_by(ChangeItem.id)
    )
    return list(db.execute(stmt).scalars())


def create_change_item(db: Session, change_set_id: int, item: dict) -> ChangeItem:
    row = ChangeItem(
        change_set_id=change_set_id,
        change_kind=item["change_kind"],
        entity_type=item["entity_type"],
        entity_key=item["entity_key"],
        before_json=item.get("before_json"),
        after_json=item.get("after_json"),
        risk_hint=item.get("risk_hint", "NONE"),
        source_refs_json=item.get("source_refs_json", "[]"),
    )
    db.add(row)
    db.flush()
    return row


def create_impact_run(
    db: Session,
    project_id: int,
    mission_id: int,
    change_set_id: int,
    algorithm_version: str,
    input_hash: str,
    status: str,
) -> ImpactAnalysisRun:
    row = ImpactAnalysisRun(
        project_id=project_id,
        mission_id=mission_id,
        change_set_id=change_set_id,
        algorithm_version=algorithm_version,
        input_hash=input_hash,
        status=status,
    )
    db.add(row)
    db.flush()
    return row


def get_impact_run(db: Session, impact_run_id: int) -> ImpactAnalysisRun | None:
    return db.get(ImpactAnalysisRun, impact_run_id)


def list_impact_results(db: Session, impact_run_id: int) -> list[ImpactResult]:
    stmt = (
        select(ImpactResult)
        .where(ImpactResult.impact_run_id == impact_run_id)
        .order_by(ImpactResult.impact_score.desc(), ImpactResult.id)
    )
    return list(db.execute(stmt).scalars())


def create_impact_result(db: Session, impact_run_id: int, result: dict) -> ImpactResult:
    row = ImpactResult(
        impact_run_id=impact_run_id,
        scenario_id=result["scenario_id"],
        scenario_version_id=result["scenario_version_id"],
        impact_score=result.get("impact_score", 0.0),
        risk_level=result.get("risk_level", "P2"),
        reasons_json=result.get("reasons_json", "[]"),
        path_json=result.get("path_json", "[]"),
        decision=result.get("decision", "INCLUDE"),
    )
    db.add(row)
    db.flush()
    return row


def create_selection(
    db: Session,
    mission_id: int,
    impact_run_id: int | None,
    build_observation_id: int | None,
    selection_type: str,
    selected_json: str,
    excluded_json: str,
    fallback_reason: str | None,
    content_hash: str,
) -> RegressionSelection:
    row = RegressionSelection(
        mission_id=mission_id,
        impact_run_id=impact_run_id,
        build_observation_id=build_observation_id,
        selection_type=selection_type,
        selected_json=selected_json,
        excluded_json=excluded_json,
        fallback_reason=fallback_reason,
        content_hash=content_hash,
    )
    db.add(row)
    db.flush()
    return row


def get_selection(db: Session, selection_id: int) -> RegressionSelection | None:
    return db.get(RegressionSelection, selection_id)


def list_selection_items(
    db: Session, selection_id: int
) -> list[RegressionSelectionItem]:
    stmt = (
        select(RegressionSelectionItem)
        .where(RegressionSelectionItem.selection_id == selection_id)
        .order_by(RegressionSelectionItem.id)
    )
    return list(db.execute(stmt).scalars())


def create_selection_item(
    db: Session, selection_id: int, item: dict
) -> RegressionSelectionItem:
    row = RegressionSelectionItem(
        selection_id=selection_id,
        scenario_id=item["scenario_id"],
        scenario_version_id=item["scenario_version_id"],
        decision=item["decision"],
        reason=item.get("reason", ""),
        source=item.get("source", "SYSTEM"),
    )
    db.add(row)
    db.flush()
    return row


def count_edges_to(db: Session, project_id: int, to_type: str, to_id: int) -> int:
    stmt = select(LineageEdge).where(
        LineageEdge.project_id == project_id,
        LineageEdge.to_type == to_type,
        LineageEdge.to_id == to_id,
    )
    return len(list(db.execute(stmt).scalars()))


def latest_change_set_for_mission(
    db: Session, mission_id: int, change_type: str | None = None
) -> ChangeSet | None:
    stmt = (
        select(ChangeSet)
        .where(ChangeSet.mission_id == mission_id)
        .order_by(ChangeSet.id.desc())
    )
    if change_type is not None:
        stmt = stmt.where(ChangeSet.change_type == change_type)
    return db.execute(stmt.limit(1)).scalars().first()


def insert_edge_ignoring_dupes(
    db: Session, values: dict[str, Any]
) -> LineageEdge | None:
    """Insert a lineage edge, returning ``None`` if an identical edge already exists.

    Checks for an existing identical edge first (project + both endpoints + type)
    instead of relying on a unique-constraint rollback, so a batch backfill stays
    idempotent without wiping previously inserted edges in the same transaction.
    """
    existing = (
        db.execute(
            select(LineageEdge).where(
                LineageEdge.project_id == values["project_id"],
                LineageEdge.from_type == values["from_type"],
                LineageEdge.from_id == values["from_id"],
                LineageEdge.to_type == values["to_type"],
                LineageEdge.to_id == values["to_id"],
                LineageEdge.edge_type == values["edge_type"],
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        return None
    row = LineageEdge(**values)
    db.add(row)
    db.flush()
    return row
