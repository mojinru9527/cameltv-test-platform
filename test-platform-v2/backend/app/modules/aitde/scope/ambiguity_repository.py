"""Ambiguity / Intent repository (V30-040..V30-044)."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import (
    AmbiguityStatus,
    ReviewStatus,
    RiskLevel,
)
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityDetectionOutput,
    IntentDetectionOutput,
)
from app.modules.aitde.scope.models import Ambiguity, TestIntent


def replace_ambiguities(
    db: Session,
    mission_id: int,
    output: AmbiguityDetectionOutput,
    actor: str,
    user_id: int,
) -> list[Ambiguity]:
    for old in db.scalars(
        select(Ambiguity).where(Ambiguity.mission_id == mission_id)
    ).all():
        db.delete(old)
    db.flush()

    rows = []
    for cand in output.items:
        rows.append(
            Ambiguity(
                mission_id=mission_id,
                ambiguity_key=cand.ambiguity_key,
                title=cand.title,
                description=cand.description,
                severity=cand.severity.value,
                status=AmbiguityStatus.OPEN.value,
                candidate_options_json=json.dumps(
                    [o.model_dump() for o in cand.candidate_options], ensure_ascii=False
                ),
                source_refs_json=json.dumps(
                    [r.model_dump() for r in cand.source_refs], ensure_ascii=False
                ),
                ai_confidence=cand.confidence,
                created_by_type=actor,
            )
        )
    db.add_all(rows)
    db.flush()
    return rows


def list_ambiguities(db: Session, mission_id: int) -> list[Ambiguity]:
    rows = db.scalars(
        select(Ambiguity)
        .where(Ambiguity.mission_id == mission_id)
        .order_by(Ambiguity.id.asc())
    ).all()
    return list(rows)


def get_ambiguity(db: Session, ambiguity_id: int, mission_id: int) -> Ambiguity | None:
    return db.scalar(
        select(Ambiguity).where(
            Ambiguity.id == ambiguity_id, Ambiguity.mission_id == mission_id
        )
    )


def resolve_ambiguity(
    db: Session,
    ambiguity: Ambiguity,
    selected_option_key: str,
    resolution_note: str | None,
    status: str,
    user_id: int,
) -> Ambiguity:
    ambiguity.selected_option_json = json.dumps(
        {"key": selected_option_key}, ensure_ascii=False
    )
    ambiguity.resolution_note = resolution_note or ""
    ambiguity.status = status
    ambiguity.resolved_by = user_id
    ambiguity.resolved_at = datetime.now()
    db.commit()
    db.refresh(ambiguity)
    return ambiguity


def has_open_p0p1(db: Session, mission_id: int) -> bool:
    count = db.scalar(
        select(func.count(Ambiguity.id)).where(
            Ambiguity.mission_id == mission_id,
            Ambiguity.status == AmbiguityStatus.OPEN.value,
            Ambiguity.severity.in_([RiskLevel.P0.value, RiskLevel.P1.value]),
        )
    ) or 0
    return count > 0


def replace_intents(
    db: Session,
    mission_id: int,
    output: IntentDetectionOutput,
    actor: str,
    user_id: int,
) -> list[TestIntent]:
    for old in db.scalars(
        select(TestIntent).where(TestIntent.mission_id == mission_id)
    ).all():
        db.delete(old)
    db.flush()

    rows = []
    for cand in output.items:
        rows.append(
            TestIntent(
                mission_id=mission_id,
                intent_key=cand.intent_key,
                title=cand.title,
                business_goal=cand.business_goal,
                required_outcomes_json=json.dumps(
                    cand.required_outcomes, ensure_ascii=False
                ),
                risk_level=cand.risk_level.value,
                source_refs_json=json.dumps(
                    [r.model_dump() for r in cand.source_refs], ensure_ascii=False
                ),
                review_status=ReviewStatus.PROPOSED.value,
                created_by_type=actor,
            )
        )
    db.add_all(rows)
    db.flush()
    return rows


def list_intents(db: Session, mission_id: int) -> list[TestIntent]:
    rows = db.scalars(
        select(TestIntent)
        .where(TestIntent.mission_id == mission_id)
        .order_by(TestIntent.id.asc())
    ).all()
    return list(rows)


def get_intent(db: Session, intent_id: int, mission_id: int) -> TestIntent | None:
    return db.scalar(
        select(TestIntent).where(
            TestIntent.id == intent_id, TestIntent.mission_id == mission_id
        )
    )


def review_intent(
    db: Session,
    intent: TestIntent,
    approve: bool,
    review_comment: str | None,
    user_id: int,
) -> TestIntent:
    intent.review_status = (
        ReviewStatus.APPROVED.value if approve else ReviewStatus.REJECTED.value
    )
    if review_comment:
        intent.business_goal = intent.business_goal or ""
    intent.reviewed_by = user_id
    intent.reviewed_at = datetime.now()
    db.commit()
    db.refresh(intent)
    return intent
