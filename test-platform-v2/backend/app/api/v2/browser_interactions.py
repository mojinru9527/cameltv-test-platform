"""AITDE v2 Browser + Manual + Hybrid runtime API (V33-006/007/008/009).

Frontend surface for Observe / Manual Assist / Hybrid runs, backed by the
browser + manual services and the hybrid coordinator.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.browser import service as browser_service
from app.modules.aitde.manual import service as manual_service
from app.modules.aitde.hybrid.coordinator import HybridExecutionCoordinator
from app.modules.aitde.execution import service as exec_service
from app.schemas.common import R

router = APIRouter(prefix="/browser-sessions", tags=["AITDE - Browser"], dependencies=[Depends(require_aitde_v3)])
manual_router = APIRouter(prefix="/scenarios/{scenario_id}/manual-sessions", tags=["AITDE - Manual"], dependencies=[Depends(require_aitde_v3)])
hybrid_router = APIRouter(prefix="/scenarios/{scenario_id}/hybrid-runs", tags=["AITDE - Hybrid"], dependencies=[Depends(require_aitde_v3)])


class BrowserSessionCreate(BaseModel):
    mission_id: int
    environment_id: int
    mode: str = Field(default="OBSERVE")
    browser_type: str = "chromium"
    context_ref: str = ""


class ManualSessionCreate(BaseModel):
    run_id: int
    scenario_version_id: int
    browser_session_id: int | None = None


class ManualStepComplete(BaseModel):
    status: str
    tester_note: str = ""
    evidence_refs: list[int] = Field(default_factory=list)


class HybridRunRequest(BaseModel):
    run_id: int


@router.post("", response_model=R[dict])
def create_browser_session(
    payload: BrowserSessionCreate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    s = browser_service.create_session(
        db, current.project_id or 0, payload.mission_id, payload.environment_id,
        payload.mode, current.user.id, payload.browser_type, payload.context_ref,
    )
    return R.ok({"id": s.id, "mode": s.mode, "status": s.status})


@router.post("/{session_id}/stop", response_model=R[dict])
def stop_browser_session(
    session_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    s = browser_service.stop_session(db, session_id)
    return R.ok({"id": s.id, "status": s.status})


@router.get("/{session_id}/events", response_model=R[list])
def list_browser_events(
    session_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    events = browser_service.list_events(db, session_id)
    return R.ok(
        [
            {"id": e.id, "sequence": e.sequence, "event_type": e.event_type,
             "semantic_target_json": e.semantic_target_json, "payload_ref_json": e.payload_ref_json}
            for e in events
        ]
    )


@router.post("/{session_id}/derive-action-plan", response_model=R[dict])
def derive_action_plan(
    session_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    plan = browser_service.derive_action_plan(db, session_id)
    return R.ok(plan)


@manual_router.post("", response_model=R[dict])
def create_manual_session(
    scenario_id: int,
    payload: ManualSessionCreate,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    s = manual_service.create_session(
        db, payload.run_id, payload.scenario_version_id, current.user.id, payload.browser_session_id
    )
    return R.ok({"id": s.id, "status": s.status})


@manual_router.post("/{session_id}/steps", response_model=R[dict])
def add_manual_step(
    scenario_id: int, session_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    step = manual_service.add_step(db, session_id, "step")
    return R.ok({"id": step.id, "sequence": step.sequence, "status": step.status})


@manual_router.post("/{session_id}/steps/{step_id}/complete", response_model=R[dict])
def complete_manual_step(
    scenario_id: int, session_id: int, step_id: int,
    payload: ManualStepComplete,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    step = manual_service.complete_step(db, step_id, payload.status, payload.tester_note, payload.evidence_refs)
    return R.ok({"id": step.id, "status": step.status, "completed_at": step.completed_at.isoformat() if step.completed_at else None})


@manual_router.get("/{session_id}/steps", response_model=R[list])
def list_manual_steps(
    scenario_id: int, session_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    steps = manual_service.list_steps(db, session_id)
    return R.ok(
        [
            {"id": s.id, "sequence": s.sequence, "step_key": s.step_key,
             "status": s.status, "tester_note": s.tester_note, "evidence_refs_json": s.evidence_refs_json}
            for s in steps
        ]
    )


@hybrid_router.post("", response_model=R[dict])
def run_hybrid(
    scenario_id: int,
    payload: HybridRunRequest,
    current: CurrentUser = Depends(require_permission("execution:create")),
    db: Session = Depends(get_db),
):
    run = exec_service.get_run(db, payload.run_id, current.project_id or 0)
    state = HybridExecutionCoordinator().run(db, run, current.project_id or 0)
    return R.ok(state)
