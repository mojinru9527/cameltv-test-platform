"""AITDE v2 Ambiguity / Intent API (V30-043/V30-044)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.scope import ambiguity_service as service
from app.modules.aitde.scope.ambiguity_mapper import ambiguity_to_dict, intent_to_dict
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityResolveRequest,
    IntentReviewRequest,
)
from app.schemas.common import R

router = APIRouter(
    prefix="/missions/{mission_id}/ambiguities",
    tags=["AITDE - Ambiguity"],
    dependencies=[Depends(require_aitde_v3)],
)
intents_router = APIRouter(
    prefix="/missions/{mission_id}/intents",
    tags=["AITDE - Intent"],
    dependencies=[Depends(require_aitde_v3)],
)
resolve_router = APIRouter(
    prefix="/ambiguities",
    tags=["AITDE - Ambiguity"],
    dependencies=[Depends(require_aitde_v3)],
)
intent_review_router = APIRouter(
    prefix="/intents",
    tags=["AITDE - Intent"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.post("/analyze", response_model=R[dict])
def analyze(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    counts = service.analyze(db, mission_id, current.project_id or 0, current.user.id)
    from app.modules.aitde.intelligence.runner import latest_operation_id

    counts["operation_id"] = latest_operation_id(
        db, mission_id, current.project_id or 0, "ambiguity:intent:analyze"
    )
    return R.ok(counts)


@router.get("", response_model=R[dict])
def list_ambiguities(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    rows = service.list_ambiguities(db, mission_id)
    return R.ok([ambiguity_to_dict(a) for a in rows])


@resolve_router.post("/{ambiguity_id}/resolve", response_model=R[dict])
def resolve_ambiguity(
    ambiguity_id: int,
    payload: AmbiguityResolveRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    row = service.resolve_ambiguity(
        db, ambiguity_id, current.project_id or 0, current.user.id, payload
    )
    return R.ok(ambiguity_to_dict(row))


@intents_router.get("", response_model=R[dict])
def list_intents(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    rows = service.list_intents(db, mission_id)
    return R.ok([intent_to_dict(i) for i in rows])


@intent_review_router.post("/{intent_id}/review", response_model=R[dict])
def review_intent(
    intent_id: int,
    payload: IntentReviewRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    row = service.review_intent(
        db, intent_id, current.project_id or 0, current.user.id, payload
    )
    return R.ok(intent_to_dict(row))

