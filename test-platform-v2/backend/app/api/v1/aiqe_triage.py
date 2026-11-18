"""AUD-014/015/017/018/019/020/013：v1.5 §06 目标契约的 REST 面。

所有路由都复用已交付的 service（不新增业务逻辑），并遵守统一的：
project scope（`current.project_id`）、RBAC（`menu:aiqe_runs` / `defect:update`）、
错误映射（400/403/404/422）、以及"前端不得自报事实"的约束。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services import (
    noise_intelligence,
    triage_service,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe", tags=["AIQE Capabilities"])

_console = require_permission("menu:aiqe_runs")
_edit = require_permission("defect:update")


def _bad(message: str, status: int = 400) -> APIException:
    return APIException(code=status, msg=message, http_status=status)


# ── Experiments (AUD-004) ───────────────────────────────
class ExperimentIn(BaseModel):
    experiment_key: str = Field(min_length=2, max_length=2)
    change: dict[str, str]
    idempotency_key: str = Field(min_length=1, max_length=128)
    hypothesis_id: str | None = None
    profile_id: str | None = None


@router.post(
    "/runs/{run_id}/experiments", response_model=R[dict], summary="创建反事实实验（E1–E6）"
)
def create_experiment_api(
    run_id: str,
    body: ExperimentIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = triage_service.create_experiment(
            db,
            experiment_key=body.experiment_key,
            change=body.change,
            idempotency_key=body.idempotency_key,
            baseline_run_id=run_id,
            hypothesis_id=body.hypothesis_id,
            profile_id=body.profile_id,
            triage_case_id=None,
        )
    except triage_service.ExperimentError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_experiment_out(row))


@router.post(
    "/experiments/{experiment_id}/launch", response_model=R[dict], summary="创建真实验证 Run"
)
def launch_experiment_api(
    experiment_id: str,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = triage_service.launch_experiment(db, experiment_id)
    except triage_service.ExperimentError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok(_experiment_out(row))


@router.post(
    "/experiments/{experiment_id}/sync", response_model=R[dict], summary="按验证 Run 终态收敛实验"
)
def sync_experiment_api(
    experiment_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    try:
        row = triage_service.sync_experiment_result(db, experiment_id)
    except triage_service.ExperimentError as exc:
        raise _bad(str(exc), 404) from None
    db.commit()
    return R.ok(_experiment_out(row))


def _experiment_out(row) -> dict:
    return {
        "id": row.id,
        "experiment_key": row.experiment_key,
        "changed_dimension": row.changed_dimension,
        "changed_value": row.changed_value,
        "status": row.status,
        "baseline_run_id": row.baseline_run_id,
        "verification_run_id": row.verification_run_id,
        "snapshot_diff": row.snapshot_diff_json,
        "experiment_result": row.experiment_result,
        "error_code": row.error_code,
    }


# ── Triage / Observations (AUD-019) ─────────────────────
class DetectIn(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    node_run_id: str | None = None


@router.post(
    "/runs/{run_id}/observations", response_model=R[dict], summary="运行干扰检测并落库（AUD-019）"
)
def detect_observations_api(
    run_id: str,
    body: DetectIn,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    detections = noise_intelligence.detect_categories(body.payload)
    rows = noise_intelligence.persist_observations(
        db,
        project_id=current.project_id or 0,
        run_id=run_id,
        node_run_id=body.node_run_id,
        detections=detections,
    )
    db.commit()
    return R.ok(
        {
            "run_id": run_id,
            "items": [
                {
                    "id": row.id,
                    "detector_key": row.detector_key,
                    "category": row.category,
                    "severity": row.severity,
                    "recommended_experiment": row.recommended_experiment,
                }
                for row in rows
            ],
        }
    )


@router.get("/runs/{run_id}/observations", response_model=R[dict], summary="干扰观测列表")
def list_observations_api(
    run_id: str,
    current: CurrentUser = Depends(_console),
    db: Session = Depends(get_db),
):
    rows = noise_intelligence.list_observations(
        db, project_id=current.project_id or 0, run_id=run_id
    )
    return R.ok(
        {
            "items": [
                {
                    "id": row.id,
                    "detector_key": row.detector_key,
                    "category": row.category,
                    "severity": row.severity,
                    "window_start": row.window_start,
                    "window_end": row.window_end,
                    "evidence_refs": row.evidence_refs_json or [],
                    "recommended_experiment": row.recommended_experiment,
                }
                for row in rows
            ]
        }
    )


class TriageTransitionIn(BaseModel):
    target: str = Field(min_length=1, max_length=32)


@router.post("/runs/{run_id}/triage", response_model=R[dict], summary="创建 TriageCase")
def create_triage_api(
    run_id: str,
    node_run_id: str | None = None,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    row = noise_intelligence.create_triage_case(
        db, project_id=current.project_id or 0, run_id=run_id, node_run_id=node_run_id
    )
    db.commit()
    return R.ok({"id": row.id, "run_id": row.run_id, "status": row.status})


@router.post(
    "/triage/{triage_id}/transition", response_model=R[dict], summary="TriageCase 状态迁移"
)
def transition_triage_api(
    triage_id: str,
    body: TriageTransitionIn,
    current: CurrentUser = Depends(_edit),
    db: Session = Depends(get_db),
):
    try:
        row = noise_intelligence.transition_triage_case(
            db,
            triage_id=triage_id,
            project_id=current.project_id or 0,
            target=body.target,
        )
    except noise_intelligence.NoiseIntelligenceError as exc:
        db.rollback()
        raise _bad(str(exc)) from None
    db.commit()
    return R.ok({"id": row.id, "status": row.status})


