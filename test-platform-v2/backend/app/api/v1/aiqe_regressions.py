"""batch-341 + AUD-009/010：AIQE 缺陷修复回归 API。

- ``POST /aiqe/defects/{defect_id}/regressions``：服务端 fingerprint 幂等 + 部署证明 +
  范围冻结（AUD-009）；
- ``GET /aiqe/regressions/{id}/comparison``：不可变 Before/After 快照（AUD-010）；
- ``POST /aiqe/regressions/{id}/cancel``：有权限的取消（AUD-010）；
- 旧 ``POST /aiqe/regressions`` 保留为兼容别名。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.aiqe.services.regression_service import (
    RegressionError,
    RegressionNotFound,
    cancel_regression,
    create_regression_request,
    get_regression,
    get_verification_run,
    load_comparison,
    list_regressions,
)
from app.aiqe.services.regression_terminal import (
    regression_owner_project,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe", tags=["AIQE Regression"])

_console_access = require_permission("menu:aiqe_runs")


class RegressionIn(BaseModel):
    defect_id: int
    fixed_sha: str = Field(min_length=7, max_length=64)
    previous_run_id: str | None = None
    source_run_id: str | None = None
    reason: str = Field(default="", max_length=2000)
    environment_snapshot: dict = Field(default_factory=dict)


class RegressionRequestIn(BaseModel):
    fixed_sha: str = Field(min_length=1, max_length=64)
    target_environment_id: int | None = None
    source_run_id: str | None = None
    scope: str = Field(default="DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT", max_length=40)
    selected_case_ids: list[str] = Field(default_factory=list)
    reason: str = Field(default="", max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=128)
    #: V16-014-R2：A5 证据化影响分析（checksum 必须匹配），用于扩大 mandatory scope。
    #: 兼容旧调用方；新调用方应只传 impact_base_sha，由服务端重算。
    impact_analysis: dict | None = None
    #: V16-014：服务端从 base_sha..fixed_sha 的真实 Git diff 重算影响分析。
    impact_base_sha: str | None = Field(default=None, max_length=64)


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
        "deployed_sha": row.deployed_sha,
        "target_environment_id": row.target_environment_id,
        "source_run_id": row.source_run_id,
        "previous_run_id": row.previous_run_id,
        "verification_run_id": row.verification_run_id,
        "status": row.status,
        "scope": row.scope,
        "scope_hash": row.scope_hash,
        "mandatory_case_ids": row.mandatory_case_ids_json or [],
        "excluded": row.excluded_json or [],
        "blockers": row.blockers_json or [],
        "suggestion": row.suggestion,
        "completed_at": row.completed_at,
        "comparison_snapshot_id": row.comparison_snapshot_id,
        "created_at": row.created_at,
        "run": _run_out(get_verification_run(db, row)),
    }


@router.post(
    "/defects/{defect_id}/regressions",
    response_model=R[dict],
    summary="发起缺陷修复回归（幂等 + 部署证明 + 范围冻结）",
)
def post_defect_regression(
    defect_id: int,
    body: RegressionRequestIn,
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row, run, created = create_regression_request(
            db,
            project_id=current.project_id or 0,
            defect_id=defect_id,
            fixed_sha=body.fixed_sha,
            target_environment_id=body.target_environment_id,
            source_run_id=body.source_run_id,
            scope=body.scope,
            selected_case_ids=body.selected_case_ids,
            reason=body.reason,
            idempotency_key=idempotency_header or body.idempotency_key,
            actor_id=getattr(current.user, "id", None),
            impact_analysis=body.impact_analysis,
            impact_base_sha=body.impact_base_sha,
        )
    except RegressionError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    db.commit()
    payload = _regression_out(db, row)
    payload["run_id"] = run.id if run is not None else None
    payload["created"] = created
    payload["blocked"] = row.status == "BLOCKED"
    return R.ok(payload)


@router.post("/regressions", response_model=R[dict], summary="创建缺陷修复回归（兼容旧入口）")
def post_regression(
    body: RegressionIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row, run, created = create_regression_request(
            db,
            project_id=current.project_id or 0,
            defect_id=body.defect_id,
            fixed_sha=body.fixed_sha,
            source_run_id=body.source_run_id or body.previous_run_id,
            reason=body.reason,
            selected_case_ids=[],
        )
    except RegressionError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    db.commit()
    payload = _regression_out(db, row)
    payload["run_id"] = run.id if run is not None else None
    payload["created"] = created
    return R.ok(payload)


@router.get("/regressions", response_model=R[list], summary="回归请求列表")
def get_regressions(
    defect_id: int | None = Query(default=None),
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_regressions(db, current.project_id or 0, defect_id=defect_id)
    return R.ok([_regression_out(db, row) for row in rows])


@router.get("/regressions/{regression_id}", response_model=R[dict], summary="回归请求详情")
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


@router.get(
    "/regressions/{regression_id}/comparison",
    response_model=R[dict],
    summary="Before/After 对比快照（不可变）",
)
def get_regression_comparison(
    regression_id: int,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    try:
        row, snapshot = load_comparison(
            db, regression_id=regression_id, project_id=current.project_id or 0
        )
    except RegressionNotFound:
        raise APIException(
            code=404, msg=f"回归请求不存在: {regression_id}", http_status=404
        ) from None
    if snapshot is None:
        return R.ok(
            {
                "regression_id": row.id,
                "status": row.status,
                "available": False,
                "reason": "VERIFICATION_RUN_NOT_TERMINAL",
            }
        )
    return R.ok(
        {
            "regression_id": row.id,
            "status": row.status,
            "available": True,
            "snapshot": {
                "id": snapshot.id,
                "outcome": snapshot.outcome,
                "fixed_sha": snapshot.fixed_sha,
                "deployed_sha": snapshot.deployed_sha,
                "workflow_checksum": snapshot.workflow_checksum,
                "source_run_id": snapshot.source_run_id,
                "regression_run_id": snapshot.regression_run_id,
                "assertion_diff": snapshot.assertion_diff_json,
                "node_attempt_diff": snapshot.node_attempt_diff_json,
                "new_failures": snapshot.new_failures_json,
                "fixed_failures": snapshot.fixed_failures_json,
                "blocked": snapshot.blocked_json,
                "evidence_refs": snapshot.evidence_refs_json,
                "created_at": snapshot.created_at,
            },
            "suggestion": row.suggestion,
            "defect_project_id": regression_owner_project(db, row),
        }
    )


@router.post(
    "/regressions/{regression_id}/cancel",
    response_model=R[dict],
    summary="取消回归（有权限）",
)
def cancel_regression_api(
    regression_id: int,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = cancel_regression(
            db, regression_id=regression_id, project_id=current.project_id or 0
        )
    except RegressionNotFound:
        raise APIException(
            code=404, msg=f"回归请求不存在: {regression_id}", http_status=404
        ) from None
    except RegressionError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    db.commit()
    return R.ok(_regression_out(db, row))
