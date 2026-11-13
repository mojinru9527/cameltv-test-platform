"""batch-341（M9-2）：AIQE 缺陷修复回归 API（创建回归请求 + verification Run 查询）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services.regression_service import (
    RegressionError,
    RegressionNotFound,
    create_regression,
    get_regression,
    get_verification_run,
    list_regressions,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/regressions", tags=["AIQE Regression"])

_console_access = require_permission("menu:aiqe_runs")


class RegressionIn(BaseModel):
    defect_id: int
    fixed_sha: str = Field(min_length=7, max_length=64)
    previous_run_id: str | None = None
    environment_snapshot: dict = Field(default_factory=dict)


def _run_out(run) -> dict | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "run_key": run.run_key,
        "status": run.status,
        "outcome": run.outcome,
        "source_type": run.source_type,
        "commit_sha": run.commit_sha,
        "retest_of": run.retest_of,
    }


def _regression_out(db: Session, row) -> dict:
    return {
        "id": row.id,
        "defect_id": row.defect_id,
        "fixed_sha": row.fixed_sha,
        "previous_run_id": row.previous_run_id,
        "verification_run_id": row.verification_run_id,
        "status": row.status,
        "created_at": row.created_at,
        "run": _run_out(get_verification_run(db, row)),
    }


@router.post("", response_model=R[dict], summary="创建缺陷修复回归（含 verification Run）")
def post_regression(
    body: RegressionIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row, run = create_regression(
            db,
            project_id=current.project_id or 0,
            defect_id=body.defect_id,
            fixed_sha=body.fixed_sha,
            previous_run_id=body.previous_run_id,
            environment_snapshot=body.environment_snapshot,
        )
    except RegressionError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    payload = _regression_out(db, row)
    payload["run_id"] = run.id
    return R.ok(payload)


@router.get("", response_model=R[list], summary="回归请求列表")
def get_regressions(
    defect_id: int | None = Query(default=None),
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_regressions(db, current.project_id or 0, defect_id=defect_id)
    return R.ok([_regression_out(db, row) for row in rows])


@router.get("/{regression_id}", response_model=R[dict], summary="回归请求详情")
def get_regression_detail(
    regression_id: int,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    try:
        row = get_regression(db, regression_id, current.project_id or 0)
    except RegressionNotFound:
        raise APIException(
            code=404, msg=f"回归请求不存在: {regression_id}", http_status=404
        ) from None
    return R.ok(_regression_out(db, row))
