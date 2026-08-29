"""AITDE v2 Execution API (V31-002/V31-011/PR31-07).

Unified run surface: create (bind scenario_version + contract_version +
environment_snapshot), detail, cancel, retry, timeline steps, oracle
assertions, and mission-scoped run list. Mounted under ``/api/v2``, gated, and
obeying the tenant boundary via ``X-Project-Id``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.execution import repository, service
from app.modules.aitde.execution.mapper import (
    assertion_to_dict,
    run_to_dict,
    step_to_dict,
)
from app.modules.aitde.execution.schemas import RunCreate
from app.schemas.common import R

router = APIRouter(tags=["AITDE - Execution"], dependencies=[Depends(require_aitde_v3)])


@router.post("/scenarios/{scenario_id}/runs", response_model=R[dict])
def create_run(
    scenario_id: int,
    payload: RunCreate,
    current: CurrentUser = Depends(require_permission("execution:create")),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data["scenario_id"] = scenario_id
    row = service.create_run(
        db, data, project_id=current.project_id or 0, user_id=current.user.id
    )
    return R.ok(run_to_dict(row))


@router.get("/runs/{run_id}", response_model=R[dict])
def get_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    row = service.get_run(db, run_id, current.project_id or 0)
    return R.ok(run_to_dict(row))


@router.post("/runs/{run_id}/cancel", response_model=R[dict])
def cancel_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:cancel")),
    db: Session = Depends(get_db),
):
    row = service.cancel_run(db, run_id, current.project_id or 0)
    return R.ok(run_to_dict(row))


@router.post("/runs/{run_id}/retry", response_model=R[dict])
def retry_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:retry")),
    db: Session = Depends(get_db),
):
    row = service.retry_run(db, run_id, current.project_id or 0, current.user.id)
    return R.ok(run_to_dict(row))


@router.get("/runs/{run_id}/steps", response_model=R[dict])
def list_steps(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    items = repository.list_steps(db, run_id, current.project_id or 0)
    return R.ok({"items": [step_to_dict(s) for s in items]})


@router.get("/runs/{run_id}/assertions", response_model=R[dict])
def list_assertions(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    items = repository.list_assertions(db, run_id, current.project_id or 0)
    return R.ok({"items": [assertion_to_dict(a) for a in items]})


@router.get("/missions/{mission_id}/executions", response_model=R[dict])
def list_mission_runs(
    mission_id: int,
    outcome: str = Query(""),
    runtime_status: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    items, total = service.list_runs(
        db,
        current.project_id or 0,
        mission_id=mission_id,
        outcome=outcome or None,
        runtime_status=runtime_status or None,
        page=page,
        page_size=page_size,
    )
    return R.ok(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [run_to_dict(r) for r in items],
        }
    )
