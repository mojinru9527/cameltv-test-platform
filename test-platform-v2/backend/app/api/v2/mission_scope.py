"""AITDE v2 Scope API (V30-036)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.scope import service
from app.modules.aitde.scope.mapper import scope_item_to_dict
from app.modules.aitde.scope.schemas import (
    ScopeAnalysisRequest,
    ScopeBulkReviewRequest,
)
from app.schemas.common import R

router = APIRouter(
    prefix="/missions/{mission_id}/scope",
    tags=["AITDE - Scope"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.post("/analyze", response_model=R[dict])
def analyze_scope(
    mission_id: int,
    payload: ScopeAnalysisRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    items = service.analyze_scope(
        db, mission_id, current.project_id or 0, current.user.id
    )
    from app.modules.aitde.intelligence.runner import latest_operation_id

    op_id = latest_operation_id(
        db, mission_id, current.project_id or 0, "scope:analyze"
    )
    return R.ok({"operation_id": op_id, "status": "COMPLETED", "items": len(items)})


@router.get("", response_model=R[dict])
def get_scope(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    rows, summary = service.list_scope(db, mission_id)
    return R.ok(
        {
            "items": [scope_item_to_dict(r) for r in rows],
            "summary": summary.model_dump(),
        }
    )


@router.post("/reviews", response_model=R[dict])
def review_scope(
    mission_id: int,
    payload: ScopeBulkReviewRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    summary = service.review_scope(
        db, mission_id, current.project_id or 0, current.user.id, payload
    )
    return R.ok(summary.model_dump())


@router.post("/complete", response_model=R[dict])
def complete_scope(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    summary = service.complete_policy(db, mission_id)
    return R.ok(summary.model_dump())

