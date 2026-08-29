"""Scope repository (V30-030/V30-036)."""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import (
    ReviewStatus,
    ScopeDecision,
)
from app.modules.aitde.scope.models import ScopeItem
from app.modules.aitde.scope.schemas import ScopeAnalysisOutput, ScopeSummary


def replace_items(
    db: Session,
    mission_id: int,
    output: ScopeAnalysisOutput,
    actor: str,
    user_id: int,
) -> list[ScopeItem]:
    """Delete existing scope items for a mission and persist the new analysis."""
    for old in db.scalars(
        select(ScopeItem).where(ScopeItem.mission_id == mission_id)
    ).all():
        db.delete(old)
    db.flush()

    rows: list[ScopeItem] = []
    for cand in output.items:
        rows.append(
            ScopeItem(
                mission_id=mission_id,
                scope_key=cand.scope_key,
                scope_type=cand.scope_type.value,
                name=cand.name,
                decision=cand.decision.value,
                test_depth=cand.test_depth.value,
                risk_level=cand.risk_level.value,
                reason=cand.reason,
                ai_confidence=cand.confidence,
                review_status=ReviewStatus.PROPOSED.value,
                source_refs_json=json.dumps(
                    [r.model_dump() for r in cand.source_refs], ensure_ascii=False
                ),
                created_by_type=actor,
                created_by=user_id,
            )
        )
    db.add_all(rows)
    db.flush()
    return rows


def list_items(db: Session, mission_id: int) -> list[ScopeItem]:
    rows = db.scalars(
        select(ScopeItem)
        .where(ScopeItem.mission_id == mission_id)
        .order_by(ScopeItem.risk_level.asc(), ScopeItem.id.asc())
    ).all()
    return list(rows)


def get_item(db: Session, scope_id: int, mission_id: int) -> ScopeItem | None:
    return db.scalar(
        select(ScopeItem).where(
            ScopeItem.id == scope_id, ScopeItem.mission_id == mission_id
        )
    )


def summary(db: Session, mission_id: int) -> ScopeSummary:
    total = db.scalar(
        select(func.count(ScopeItem.id)).where(ScopeItem.mission_id == mission_id)
    ) or 0
    approved = db.scalar(
        select(func.count(ScopeItem.id)).where(
            ScopeItem.mission_id == mission_id,
            ScopeItem.review_status == ReviewStatus.APPROVED.value,
        )
    ) or 0
    rejected = db.scalar(
        select(func.count(ScopeItem.id)).where(
            ScopeItem.mission_id == mission_id,
            ScopeItem.review_status == ReviewStatus.REJECTED.value,
        )
    ) or 0
    include_count = db.scalar(
        select(func.count(ScopeItem.id)).where(
            ScopeItem.mission_id == mission_id,
            ScopeItem.decision == ScopeDecision.INCLUDE.value,
        )
    ) or 0
    exclude_count = db.scalar(
        select(func.count(ScopeItem.id)).where(
            ScopeItem.mission_id == mission_id,
            ScopeItem.decision == ScopeDecision.EXCLUDE.value,
        )
    ) or 0
    proposed = total - approved - rejected
    progress = (approved + rejected) / total if total else 0.0
    return ScopeSummary(
        total=total,
        approved=approved,
        rejected=rejected,
        proposed=max(proposed, 0),
        review_progress=round(progress, 4),
        include_count=include_count,
        exclude_count=exclude_count,
    )


def has_items(db: Session, mission_id: int) -> bool:
    return bool(
        db.scalar(
            select(func.count(ScopeItem.id)).where(ScopeItem.mission_id == mission_id)
        )
    )
