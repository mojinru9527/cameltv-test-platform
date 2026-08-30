"""AITDE v2 Smart Regression / Impact Analysis API (V37).

ChangeSet detection, impact analysis, regression selection, coverage guard, and
smart-campaign freeze. Mounted under ``/api/v2`` and feature-gated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.smart_regression import service
from app.modules.aitde.smart_regression.schemas import (
    CampaignIn,
    DetectIn,
    EdgeAddIn,
    HistoricalRiskDetectIn,
    SelectionIn,
)
from app.schemas.common import R

router = APIRouter(
    tags=["AITDE - Smart Regression"], dependencies=[Depends(require_aitde_v3)]
)


def _issue_404(msg: str) -> None:
    from app.core.exceptions import APIException

    raise APIException(code=404, msg=msg, http_status=404)


@router.post("/missions/{mission_id}/changes/detect", response_model=R[dict])
def detect_changes(
    mission_id: int,
    payload: DetectIn,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.ChangeSetService.detect(
            db,
            current.project_id or 0,
            mission_id,
            payload.change_type,
            payload.baseline or {},
            payload.current or {},
            payload.source_from_ref,
            payload.source_to_ref,
        )
    )


@router.post("/missions/{mission_id}/changes/detect-risk", response_model=R[dict])
def detect_risk(
    mission_id: int,
    payload: HistoricalRiskDetectIn,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.detect_risk_signals(
            db, mission_id, [s.model_dump() for s in payload.signals]
        )
    )


@router.get("/change-sets/{change_set_id}", response_model=R[dict])
def get_change_set(
    change_set_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    data = service.ChangeSetService.get(db, change_set_id)
    if data is None:
        _issue_404("ChangeSet 不存在")
    return R.ok(data)


@router.post("/change-sets/{change_set_id}/impact", response_model=R[dict])
def analyze_impact(
    change_set_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    changeset = service.ChangeSetService.get(db, change_set_id)
    if changeset is None:
        _issue_404("ChangeSet 不存在")
    return R.ok(
        service.ImpactAnalyzer.analyze(
            db, current.project_id or 0, changeset["mission_id"], change_set_id
        )
    )


@router.get("/impact-runs/{impact_run_id}", response_model=R[dict])
def get_impact_run(
    impact_run_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    data = service.ImpactAnalyzer.get_run(db, impact_run_id)
    if data is None:
        _issue_404("ImpactRun 不存在")
    return R.ok(data)


@router.get(
    "/impact-runs/{impact_run_id}/scenarios/{scenario_id}/explanation",
    response_model=R[dict],
)
def explain_impact(
    impact_run_id: int,
    scenario_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    data = service.ImpactExplanationService.explain(db, impact_run_id, scenario_id)
    if data is None:
        _issue_404("ImpactRun 不存在")
    return R.ok(data)


@router.post("/impact-runs/{impact_run_id}/selections", response_model=R[dict])
def create_selection(
    impact_run_id: int,
    payload: SelectionIn,
    current: CurrentUser = Depends(require_permission("execution:create")),
    db: Session = Depends(get_db),
):
    run = service.ImpactAnalyzer.get_run(db, impact_run_id)
    if run is None:
        _issue_404("ImpactRun 不存在")
    return R.ok(
        service.RegressionSelector.select(
            db,
            current.project_id or 0,
            run["mission_id"],
            impact_run_id,
            payload.selection_type,
            payload.build_observation_id,
        )
    )


@router.post("/regression-selections/{selection_id}/campaign", response_model=R[dict])
def create_campaign(
    selection_id: int,
    payload: CampaignIn,
    current: CurrentUser = Depends(require_permission("execution:create")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.SmartRegressionCampaignFactory.create_campaign(
            db,
            current.project_id or 0,
            selection_id,
            payload.name,
            payload.environment_id,
        )
    )


@router.get("/regression-selections/{selection_id}", response_model=R[dict])
def get_selection(
    selection_id: int,
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    data = service.RegressionSelector.get(db, selection_id)
    if data is None:
        _issue_404("Selection 不存在")
    return R.ok(data)


@router.get("/regression-selections/{selection_id}/guard", response_model=R[dict])
def guard_selection(
    selection_id: int,
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    selection = service.RegressionSelector.get(db, selection_id)
    if selection is None:
        _issue_404("Selection 不存在")
    return R.ok(
        service.CoverageGuard.guard(
            db, current.project_id or 0, selection["mission_id"], selection_id, []
        )
    )


@router.get("/missions/{mission_id}/lineage", response_model=R[dict])
def get_lineage(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.lineage_list(db, current.project_id or 0, mission_id))


@router.post("/missions/{mission_id}/lineage/backfill", response_model=R[dict])
def backfill_lineage(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.LineageBackfillService.backfill(db, current.project_id or 0, mission_id)
    )


@router.post("/missions/{mission_id}/lineage/edges", response_model=R[dict])
def add_edge(
    mission_id: int,
    payload: EdgeAddIn,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    edge = service.LineageService.add_edge(
        db,
        current.project_id or 0,
        mission_id,
        payload.from_type,
        payload.from_id,
        payload.to_type,
        payload.to_id,
        payload.edge_type,
        payload.source_refs,
        payload.confidence,
    )
    return R.ok({"created": edge is not None, "edge_id": edge.id if edge else None})
