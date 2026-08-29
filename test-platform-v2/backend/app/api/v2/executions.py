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
from app.modules.aitde.evidence.service import list_evidence
from app.modules.aitde.evidence.replay import build_replay_view, get_manifest, manifest_dict
from app.modules.aitde.execution import legacy_bridge, repository, service
from app.modules.aitde.execution.mapper import (
    assertion_to_dict,
    evidence_to_dict,
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


@router.get("/runs/{run_id}/evidence", response_model=R[dict])
def list_run_evidence(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    items = list_evidence(db, run_id, current.project_id or 0)
    return R.ok({"items": [evidence_to_dict(e) for e in items]})


@router.get("/runs/{run_id}/replay", response_model=R[dict])
def replay_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    manifest = get_manifest(db, run_id, current.project_id or 0)
    return R.ok(
        {
            "manifest": manifest_dict(manifest),
            "hash": manifest.manifest_hash,
            "view": build_replay_view(manifest_dict(manifest)),
        }
    )


@router.post("/runs/{run_id}/finish", response_model=R[dict])
def finish_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:update")),
    db: Session = Depends(get_db),
):
    """Transition to FINISHED and compute the frozen Outcome from the run's
    persisted assertions + evidence completeness (never an AI judgment)."""
    run = service.get_run(db, run_id, current.project_id or 0)
    assertions = repository.list_assertions(db, run_id, current.project_id or 0)
    evidence = list_evidence(db, run_id, current.project_id or 0)
    sanitized_ok = (
        len(evidence) > 0 and all(e.sanitization_status == "SANITIZED" for e in evidence)
    )
    outcome = service.compute_outcome(assertions, sanitized_ok)
    updated = service.finish_run(
        db, run_id, current.project_id or 0, outcome_str=outcome
    )
    return R.ok(run_to_dict(updated))


@router.post("/legacy-executions/{legacy_type}/{legacy_id}/link", response_model=R[dict])
def link_legacy_execution(
    legacy_type: str,
    legacy_id: int,
    run_id: int = Query(..., description="unified run to link"),
    current: CurrentUser = Depends(require_permission("execution:update")),
    db: Session = Depends(get_db),
):
    if legacy_type == "API_TASK_ITEM":
        result = legacy_bridge.bridge_api_item(
            db, project_id=current.project_id or 0, run_id=run_id, legacy_id=legacy_id
        )
    elif legacy_type == "UI_RUN":
        result = legacy_bridge.bridge_ui_run(
            db, project_id=current.project_id or 0, run_id=run_id, legacy_id=legacy_id
        )
    else:
        return R.ok({"error": f"unsupported legacy_type: {legacy_type}"})
    return R.ok(result)
