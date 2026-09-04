"""AITDE v2 Durable Runtime API (V34).

Worker registry, workflow status, run resume/retry, policy evaluation, secret-ref
metadata, and approval resolution. Mounted under ``/api/v2`` and feature-gated
(plan §8). Secret values are never accepted or returned.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.open_api import verify_api_token
from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.workflow import service
from app.modules.aitde.workflow.schemas import (
    ApprovalResolveIn,
    PolicyDecisionIn,
    PolicyProfileIn,
    RunResumeIn,
    SecretRefIn,
    WorkerHeartbeatIn,
)
from app.schemas.common import R

router = APIRouter(tags=["AITDE - Durable Runtime"], dependencies=[Depends(require_aitde_v3)])


# ── Worker registry ──────────────────────────────────────────────────────────


@router.post("/workers/heartbeat", response_model=R[dict])
def worker_heartbeat(
    payload: WorkerHeartbeatIn,
    api_token: object = Depends(verify_api_token),
    db: Session = Depends(get_db),
):
    data = service.register_worker_with_token(db, payload, api_token)
    return R.ok(data)


@router.get("/workers", response_model=R[dict])
def list_workers(
    current: CurrentUser = Depends(require_permission("workers:list")),
    db: Session = Depends(get_db),
):
    return R.ok({"items": service.list_workers(db)})


@router.get("/workers/{worker_id}", response_model=R[dict])
def get_worker(
    worker_id: int,
    current: CurrentUser = Depends(require_permission("workers:list")),
    db: Session = Depends(get_db),
):
    return R.ok(service.get_worker(db, worker_id))


@router.post("/workers/{worker_id}/drain", response_model=R[dict])
def drain_worker(
    worker_id: int,
    current: CurrentUser = Depends(require_permission("workers:manage")),
    db: Session = Depends(get_db),
):
    return R.ok(service.set_worker_status(db, worker_id, "DRAINING"))


@router.post("/workers/{worker_id}/disable", response_model=R[dict])
def disable_worker(
    worker_id: int,
    current: CurrentUser = Depends(require_permission("workers:manage")),
    db: Session = Depends(get_db),
):
    return R.ok(service.set_worker_status(db, worker_id, "DISABLED"))


# ── Workflow runs ────────────────────────────────────────────────────────────


@router.get("/workflows", response_model=R[dict])
def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("workflow:list")),
    db: Session = Depends(get_db),
):
    items, total = service.list_workflow_runs(
        db, current.project_id or 0, page, page_size
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.get("/workflows/{workflow_run_id}", response_model=R[dict])
def get_workflow(
    workflow_run_id: int,
    current: CurrentUser = Depends(require_permission("workflow:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.get_workflow_run(db, workflow_run_id, current.project_id or 0))


@router.post("/runs/{run_id}/resume", response_model=R[dict])
def resume_run(
    run_id: int,
    payload: RunResumeIn,
    current: CurrentUser = Depends(require_permission("workflow:resume")),
    db: Session = Depends(get_db),
):
    data = service.resume_run(
        db, current.project_id or 0, payload.workflow_id, payload.signal_name
    )
    return R.ok(data)


# ── Policy gateway ───────────────────────────────────────────────────────────


@router.post("/policy/evaluate", response_model=R[dict])
def evaluate_policy(
    payload: PolicyDecisionIn,
    current: CurrentUser = Depends(require_permission("policy:evaluate")),
    db: Session = Depends(get_db),
):
    return R.ok(service.evaluate_policy(db, payload))


@router.get("/policy-profiles", response_model=R[dict])
def list_policy_profiles(
    current: CurrentUser = Depends(require_permission("policy:list")),
    db: Session = Depends(get_db),
):
    return R.ok({"items": service.list_policy_profiles(db, current.project_id or 0)})


@router.post("/policy-profiles", response_model=R[dict])
def create_policy_profile(
    payload: PolicyProfileIn,
    current: CurrentUser = Depends(require_permission("policy:manage")),
    db: Session = Depends(get_db),
):
    return R.ok(service.create_policy_profile(db, payload))


# ── Secret refs ──────────────────────────────────────────────────────────────


@router.get("/secret-refs", response_model=R[dict])
def list_secret_refs(
    current: CurrentUser = Depends(require_permission("secret:list")),
    db: Session = Depends(get_db),
):
    return R.ok({"items": service.list_secret_refs(db, current.project_id or 0)})


@router.post("/secret-refs", response_model=R[dict])
def create_secret_ref(
    payload: SecretRefIn,
    current: CurrentUser = Depends(require_permission("secret:manage")),
    db: Session = Depends(get_db),
):
    return R.ok(service.create_secret_ref(db, payload))


# ── Approvals ────────────────────────────────────────────────────────────────


@router.get("/approvals", response_model=R[dict])
def list_approvals(
    current: CurrentUser = Depends(require_permission("approval:list")),
    db: Session = Depends(get_db),
):
    return R.ok({"items": service.list_approvals(db, current.project_id or 0)})


@router.post("/approvals/{approval_id}/approve", response_model=R[dict])
def approve(
    approval_id: int,
    payload: ApprovalResolveIn,
    current: CurrentUser = Depends(require_permission("approval:resolve")),
    db: Session = Depends(get_db),
):
    return R.ok(service.resolve_approval(db, approval_id, current.project_id or 0, True, payload.approved_by))


@router.post("/approvals/{approval_id}/reject", response_model=R[dict])
def reject(
    approval_id: int,
    payload: ApprovalResolveIn,
    current: CurrentUser = Depends(require_permission("approval:resolve")),
    db: Session = Depends(get_db),
):
    return R.ok(service.resolve_approval(db, approval_id, current.project_id or 0, False, payload.approved_by))
