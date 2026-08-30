"""AITDE V3.6 production repository — CRUD over the 9 evidence-plane tables.

All JSON structures are stored as JSON strings. Reads return ORM rows; callers
own materialisation to JSON. A simple, explicit data layer keeps the service
logic testable against SQLite and PostgreSQL alike.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.production_evidence import (
    EntityGraphSnapshot,
    MaskingProfile,
    MaskingRule,
    ObservedJourney,
    ObservedJourneyStep,
    ProdDataTemplate,
    ProductionObservationSession,
    ProductionQueryAudit,
    TemplateMaterialization,
)


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


# ── Observation sessions ────────────────────────────────────────────────────
def create_observation_session(db: Session, payload: dict[str, Any]) -> ProductionObservationSession:
    row = ProductionObservationSession(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_observation_session(db: Session, session_id: int) -> ProductionObservationSession | None:
    return db.get(ProductionObservationSession, session_id)


def list_observation_sessions(
    db: Session, project_id: int, status: str | None = None
) -> list[ProductionObservationSession]:
    stmt = select(ProductionObservationSession).where(
        ProductionObservationSession.project_id == project_id
    )
    if status:
        stmt = stmt.where(ProductionObservationSession.status == status)
    return list(db.scalars(stmt.order_by(ProductionObservationSession.id.desc())))


def update_observation_session(
    db: Session, session_id: int, payload: dict[str, Any]
) -> ProductionObservationSession | None:
    row = db.get(ProductionObservationSession, session_id)
    if row is None:
        return None
    for k, v in payload.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# ── Journeys ────────────────────────────────────────────────────────────────
def create_journey(db: Session, payload: dict[str, Any]) -> ObservedJourney:
    row = ObservedJourney(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_journey(db: Session, journey_id: int) -> ObservedJourney | None:
    return db.get(ObservedJourney, journey_id)


def list_journeys(
    db: Session, project_id: int, session_id: int | None = None
) -> list[ObservedJourney]:
    stmt = select(ObservedJourney).where(ObservedJourney.project_id == project_id)
    if session_id is not None:
        stmt = stmt.where(ObservedJourney.session_id == session_id)
    return list(db.scalars(stmt.order_by(ObservedJourney.id.desc())))


def create_journey_steps(db: Session, journey_id: int, steps: list[dict[str, Any]]) -> None:
    for i, step in enumerate(steps):
        payload = {"journey_id": journey_id, "sequence": i + 1}
        payload.update(step)
        row = ObservedJourneyStep(**payload)
        db.add(row)
    db.commit()


def list_journey_steps(db: Session, journey_id: int) -> list[ObservedJourneyStep]:
    stmt = select(ObservedJourneyStep).where(
        ObservedJourneyStep.journey_id == journey_id
    )
    return list(db.scalars(stmt.order_by(ObservedJourneyStep.sequence.asc())))


# ── Query audits ────────────────────────────────────────────────────────────
def create_query_audit(db: Session, payload: dict[str, Any]) -> ProductionQueryAudit:
    row = ProductionQueryAudit(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_query_audits(
    db: Session, project_id: int, limit: int = 200
) -> list[ProductionQueryAudit]:
    stmt = (
        select(ProductionQueryAudit)
        .where(ProductionQueryAudit.project_id == project_id)
        .order_by(ProductionQueryAudit.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def count_query_audits(db: Session, project_id: int) -> int:
    return (
        db.query(ProductionQueryAudit).filter(ProductionQueryAudit.project_id == project_id).count()
    )


# ── Masking ─────────────────────────────────────────────────────────────────
def create_masking_profile(db: Session, payload: dict[str, Any]) -> MaskingProfile:
    row = MaskingProfile(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_masking_profiles(db: Session, project_id: int) -> list[MaskingProfile]:
    return list(
        db.scalars(select(MaskingProfile).where(MaskingProfile.project_id == project_id))
    )


def create_masking_rule(db: Session, payload: dict[str, Any]) -> MaskingRule:
    row = MaskingRule(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_masking_rules(db: Session, profile_id: int) -> list[MaskingRule]:
    return list(
        db.scalars(
            select(MaskingRule)
            .where(MaskingRule.profile_id == profile_id)
            .order_by(MaskingRule.priority.desc())
        )
    )


# ── Entity graph snapshots ──────────────────────────────────────────────────
def create_entity_graph_snapshot(db: Session, payload: dict[str, Any]) -> EntityGraphSnapshot:
    row = EntityGraphSnapshot(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_entity_graph_snapshot(db: Session, snapshot_id: int) -> EntityGraphSnapshot | None:
    return db.get(EntityGraphSnapshot, snapshot_id)


# ── Prod templates ──────────────────────────────────────────────────────────
def create_prod_template(db: Session, payload: dict[str, Any]) -> ProdDataTemplate:
    row = ProdDataTemplate(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_prod_template(db: Session, template_id: int) -> ProdDataTemplate | None:
    return db.get(ProdDataTemplate, template_id)


def list_prod_templates(db: Session, project_id: int) -> list[ProdDataTemplate]:
    return list(
        db.scalars(
            select(ProdDataTemplate).where(ProdDataTemplate.project_id == project_id)
        )
    )


def update_prod_template(
    db: Session, template_id: int, payload: dict[str, Any]
) -> ProdDataTemplate | None:
    row = db.get(ProdDataTemplate, template_id)
    if row is None:
        return None
    for k, v in payload.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# ── Materializations ────────────────────────────────────────────────────────
def create_materialization(db: Session, payload: dict[str, Any]) -> TemplateMaterialization:
    row = TemplateMaterialization(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_materialization(db: Session, materialization_id: int) -> TemplateMaterialization | None:
    return db.get(TemplateMaterialization, materialization_id)


def update_materialization(
    db: Session, materialization_id: int, payload: dict[str, Any]
) -> TemplateMaterialization | None:
    row = db.get(TemplateMaterialization, materialization_id)
    if row is None:
        return None
    for k, v in payload.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row
