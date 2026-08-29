"""AITDE v2 Healing Proposal API (V33-011).

Action Healing surface: list proposals (optionally filtered by scenario adapter +
status) and approve / reject an OPEN action-only proposal. Oracle/contract
mutations are never approvable — the service rejects them wholesale at creation
and the approver cannot flip a REJECTED proposal.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.browser import healing_service
from app.schemas.common import R

router = APIRouter(
    prefix="/healing-proposals",
    tags=["AITDE - Healing"],
    dependencies=[Depends(require_aitde_v3)],
)


class ReviewRequest(BaseModel):
    reviewed_by: int | None = None


@router.get("", response_model=R[list])
def list_healing_proposals(
    scenario_adapter_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    proposals = healing_service.list_proposals(db, scenario_adapter_id, status)
    return R.ok([healing_service.to_dict(p) for p in proposals])


@router.post("/{proposal_id}/approve", response_model=R[dict])
def approve_healing_proposal(
    proposal_id: int,
    payload: ReviewRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    reviewed_by = payload.reviewed_by or current.user.id
    p = healing_service.approve_proposal(db, proposal_id, reviewed_by)
    return R.ok(healing_service.to_dict(p))


@router.post("/{proposal_id}/reject", response_model=R[dict])
def reject_healing_proposal(
    proposal_id: int,
    payload: ReviewRequest,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    reviewed_by = payload.reviewed_by or current.user.id
    p = healing_service.reject_proposal(db, proposal_id, reviewed_by)
    return R.ok(healing_service.to_dict(p))
