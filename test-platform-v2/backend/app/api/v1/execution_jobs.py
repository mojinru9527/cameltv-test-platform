"""执行节点任务协议（Batch 258 / B1-4）。

控制面只登记与调度：任务由本地节点用 `X-AI-Agent-Token` 认领、心跳、上报结果。
平台自身不执行浏览器/模型，也不保存被测系统凭据（ADR-0026 / 09 方案 §3.1）。

路由注册顺序（cameltv-bug-guard 铁律）：静态段 `/claim`、`/reclaim-stale`、`/node-status`
必须先于 `/{job_id}`，否则被路径参数抢匹配 → `"claim"` 解析 int 失败 → 422。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import ai_agent_service, execution_job_service

router = APIRouter(prefix="/execution-jobs", tags=["Execution Jobs"])


class JobCreateRequest(BaseModel):
    kind: str = Field(min_length=2, max_length=16)
    case_refs: list[str] = Field(default_factory=list)
    env_ref: str = Field(default="", max_length=255)
    timeout_seconds: int = Field(default=1800, ge=1, le=86400)


class NodeRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)


class ReportRequest(NodeRequest):
    status: str = Field(min_length=1, max_length=20)
    summary: str = ""
    result: dict = Field(default_factory=dict)
    evidence_bundle_id: int | None = None
    error_message: str = ""


def _project_id(current: CurrentUser) -> int:
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


def _node_scope(
    node_id: str,
    x_ai_agent_token: str | None,
    db: Session,
) -> int:
    """节点身份必须由节点令牌证明；令牌即项目作用域，因此跨项目认领在结构上不成立。"""
    if not x_ai_agent_token:
        raise HTTPException(401, "缺少 X-AI-Agent-Token")
    token = ai_agent_service.verify_agent_token(db, x_ai_agent_token)
    if token is None:
        raise HTTPException(401, "无效或已撤销的节点令牌")
    if token.agent_id != node_id:
        raise HTTPException(403, "节点令牌与 node_id 不匹配")
    return token.project_id


@router.post("", response_model=R[dict], summary="登记执行任务（控制面只登记，不执行）")
def create_job(
    body: JobCreateRequest,
    current: CurrentUser = Depends(require_permission("execution:manage")),
    db: Session = Depends(get_db),
):
    job = execution_job_service.create_job(
        db,
        project_id=_project_id(current),
        kind=body.kind,
        case_refs=body.case_refs,
        env_ref=body.env_ref,
        timeout_seconds=body.timeout_seconds,
    )
    return R.ok(execution_job_service.job_dict(job))


@router.get("", response_model=R[dict], summary="执行任务列表")
def list_jobs(
    status: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("execution:view")),
    db: Session = Depends(get_db),
):
    rows, total = execution_job_service.list_jobs(
        db, project_id=_project_id(current), status=status, kind=kind, page=page, page_size=page_size
    )
    return R.ok(
        {
            "items": [execution_job_service.job_dict(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/claim", response_model=R[dict], summary="节点认领任务")
def claim_job(
    body: NodeRequest,
    x_ai_agent_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    scope = _node_scope(body.node_id, x_ai_agent_token, db)
    job = execution_job_service.claim_job(db, node_id=body.node_id, project_id=scope)
    return R.ok(execution_job_service.job_dict(job) if job else None)


@router.post("/reclaim-stale", response_model=R[dict], summary="回收失联租约（任务回 pending）")
def reclaim_stale(
    current: CurrentUser = Depends(require_permission("execution:manage")),
    db: Session = Depends(get_db),
):
    _project_id(current)
    return R.ok({"reclaimed": execution_job_service.reclaim_stale(db)})


@router.get("/node-status", response_model=R[dict], summary="执行节点与队列状态（B1-6 数据源）")
def node_status(
    current: CurrentUser = Depends(require_permission("execution:view")),
    db: Session = Depends(get_db),
):
    project_id = _project_id(current)
    return R.ok(
        {
            **execution_job_service.node_status(db, project_id=project_id),
            "nodes": execution_job_service.list_nodes(db, project_id=project_id),
        }
    )


@router.get("/{job_id}", response_model=R[dict], summary="执行任务详情")
def get_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("execution:view")),
    db: Session = Depends(get_db),
):
    job = execution_job_service.get_job(db, project_id=_project_id(current), job_id=job_id)
    if job is None:
        raise HTTPException(404, "执行任务不存在")
    return R.ok(execution_job_service.job_dict(job))


@router.post("/{job_id}/heartbeat", response_model=R[dict], summary="节点心跳（续租）")
def heartbeat(
    job_id: int,
    body: NodeRequest,
    x_ai_agent_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _node_scope(body.node_id, x_ai_agent_token, db)
    ok = execution_job_service.heartbeat(db, job_id=job_id, node_id=body.node_id)
    if not ok:
        raise HTTPException(404, "任务不存在或不属于当前节点")
    return R.ok({"job_id": job_id, "heartbeat": True})


@router.post("/{job_id}/report", response_model=R[dict], summary="节点上报结果")
def report(
    job_id: int,
    body: ReportRequest,
    x_ai_agent_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _node_scope(body.node_id, x_ai_agent_token, db)
    job = execution_job_service.report(
        db,
        job_id=job_id,
        node_id=body.node_id,
        status=body.status,
        summary=body.summary,
        result=body.result,
        evidence_bundle_id=body.evidence_bundle_id,
        error_message=body.error_message,
    )
    if job is None:
        raise HTTPException(404, "任务不存在或不属于当前节点")
    return R.ok(execution_job_service.job_dict(job))
