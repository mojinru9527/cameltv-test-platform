from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.modules.aitde.execution.mapper import run_to_dict
from app.modules.campaign_execution.contracts import (
    ExecutionCancelRequest,
    ExecutionClaimRequest,
    ExecutionHeartbeatRequest,
    ExecutionReportRequest,
)
from app.modules.campaign_execution.service import (
    cancel_execution_run,
    claim_execution_run,
    heartbeat_execution_run,
    report_execution_run,
    start_campaign,
)

router = APIRouter(prefix="/execution", tags=["统一执行"])


@router.post("/campaigns/{campaign_id}/runs", response_model=R[dict])
def run_campaign(
    campaign_id: int,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    runs = start_campaign(db, project_id=current.project_id, campaign_id=campaign_id, user_id=current.user.id)
    return R.ok({"campaign_id": campaign_id, "run_ids": [r.id for r in runs]})


@router.post("/runs/claim", response_model=R[dict])
def claim_run(
    body: ExecutionClaimRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    run = claim_execution_run(
        db,
        project_id=current.project_id,
        runner_id=body.runner_id,
        capabilities=body.capabilities,
    )
    return R.ok({"claimed": run is not None, "run": run_to_dict(run) if run else None})


@router.post("/runs/{run_id}/heartbeat", response_model=R[dict])
def heartbeat_run(
    run_id: int,
    body: ExecutionHeartbeatRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    ok = heartbeat_execution_run(
        db,
        run_id=run_id,
        project_id=current.project_id or 0,
        runner_id=body.runner_id,
    )
    if not ok:
        raise HTTPException(409, "Run 未被该 Runner 持有")
    return R.ok({"run_id": run_id, "heartbeat": True})


@router.post("/runs/{run_id}/report", response_model=R[dict])
def report_run(
    run_id: int,
    body: ExecutionReportRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    run = report_execution_run(
        db,
        run_id=run_id,
        project_id=current.project_id or 0,
        runner_id=body.runner_id,
        runtime_status=body.runtime_status,
        outcome=body.outcome,
        error_message=body.error_message,
    )
    if run is None:
        raise HTTPException(409, "Run 未被该 Runner 持有或状态不允许上报")
    return R.ok(run_to_dict(run))


@router.post("/runs/{run_id}/cancel", response_model=R[dict])
def cancel_run(
    run_id: int,
    body: ExecutionCancelRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    run = cancel_execution_run(db, run_id=run_id, project_id=current.project_id or 0)
    if run is None:
        raise HTTPException(404, "Run 不存在或不可取消")
    return R.ok(run_to_dict(run))
