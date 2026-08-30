"""AITDE v2 Continuous Acceptance API (V35).

Environment fingerprint, build timeline, campaign, run profiles, triggers, and
Quality Gate evaluation. Mounted under ``/api/v2`` and feature-gated (plan §7).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.continuous import service
from app.modules.aitde.continuous import repository
from app.modules.aitde.continuous.schemas import (
    CampaignCreateIn,
    FingerprintCaptureIn,
    GateEvaluateIn,
    GateOverrideIn,
    RunProfileIn,
    TriggerIn,
)
from app.schemas.common import R

router = APIRouter(tags=["AITDE - Continuous Acceptance"], dependencies=[Depends(require_aitde_v3)])


@router.post("/environments/{environment_id}/fingerprints/capture", response_model=R[dict])
def capture_fingerprint(
    environment_id: int,
    payload: FingerprintCaptureIn,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.capture_fingerprint(db, environment_id, payload))


@router.get("/missions/{mission_id}/builds", response_model=R[dict])
def list_builds(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    items = repository.list_build_observations(db, mission_id)
    return R.ok({"items": [service.build_observation_to_dict(b) for b in items]})


@router.post("/campaigns", response_model=R[dict])
def create_campaign(
    payload: CampaignCreateIn,
    current: CurrentUser = Depends(require_permission("execution:create")),
    db: Session = Depends(get_db),
):
    return R.ok(service.create_campaign(db, payload))


@router.get("/campaigns/{campaign_id}", response_model=R[dict])
def get_campaign(
    campaign_id: int,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.get_campaign(db, campaign_id, current.project_id or 0))


@router.get("/missions/{mission_id}/campaigns", response_model=R[dict])
def list_campaigns(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok({"items": service.list_campaigns(db, mission_id)})


@router.post("/campaigns/{campaign_id}/run", response_model=R[dict])
def run_campaign(
    campaign_id: int,
    current: CurrentUser = Depends(require_permission("execution:create")),
    db: Session = Depends(get_db),
):
    # Selection becomes immutable once the run starts.
    row = repository.get_campaign(db, campaign_id, current.project_id or 0)
    if row is None:
        from app.core.exceptions import APIException

        raise APIException(code=404, msg="Campaign 不存在", http_status=404)
    updated = repository.update_campaign(db, row, {"status": "RUNNING"})
    return R.ok(service.campaign_to_dict(updated))


@router.post("/run-profiles", response_model=R[dict])
def create_run_profile(
    payload: RunProfileIn,
    current: CurrentUser = Depends(require_permission("execution:create")),
    db: Session = Depends(get_db),
):
    return R.ok(service.create_run_profile(db, payload))


@router.get("/run-profiles", response_model=R[dict])
def list_run_profiles(
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok({"items": service.list_run_profiles(db, current.project_id or 0)})


@router.post("/triggers", response_model=R[dict])
def create_trigger(
    payload: TriggerIn,
    current: CurrentUser = Depends(require_permission("mission:create")),
    db: Session = Depends(get_db),
):
    return R.ok(service.create_trigger(db, payload))


@router.get("/triggers", response_model=R[dict])
def list_triggers(
    current: CurrentUser = Depends(require_permission("mission:list")),
    db: Session = Depends(get_db),
):
    return R.ok({"items": service.list_triggers(db, current.project_id or 0)})


@router.get("/missions/{mission_id}/acceptance", response_model=R[dict])
def get_acceptance(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    items = repository.list_gate_results(db, mission_id, limit=1)
    return R.ok({"items": [service.gate_result_to_dict(g) for g in items]})


@router.post("/missions/{mission_id}/quality-gates/evaluate", response_model=R[dict])
def evaluate_gate(
    mission_id: int,
    payload: GateEvaluateIn,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.evaluate_gate(
            db,
            current.project_id or 0,
            mission_id,
            payload.campaign_id,
            payload.build_observation_id,
        )
    )


@router.get("/quality-gate-results/{result_id}", response_model=R[dict])
def get_gate_result(
    result_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    row = repository.get_gate_result(db, result_id, 0)
    if row is None:
        from app.core.exceptions import APIException

        raise APIException(code=404, msg="Gate result 不存在", http_status=404)
    return R.ok(service.gate_result_to_dict(row))


@router.post("/quality-gate-results/{result_id}/override", response_model=R[dict])
def override_gate(
    result_id: int,
    payload: GateOverrideIn,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    row = repository.get_gate_result(db, result_id, 0)
    if row is None:
        from app.core.exceptions import APIException

        raise APIException(code=404, msg="Gate result 不存在", http_status=404)
    updated = repository.update_gate_result(
        db,
        row,
        {
            "override_status": payload.override_status,
            "override_by": payload.override_by,
            "override_reason": payload.override_reason,
        },
    )
    return R.ok(service.gate_result_to_dict(updated))
