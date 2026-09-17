"""AI Agent 控制面（Batch 248）。

平台不再执行 LLM：AI 任务以 AiJob 派发，本地 Agent（本地 ChatGPT 客户端）
用 `X-AI-Agent-Token` 认领、心跳、上报结果；平台只保存与展示结果。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import ai_agent_service

router = APIRouter(prefix="/ai", tags=["AI Agent"])


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)


class AgentTokenRevokeRequest(BaseModel):
    token_id: int


class JobImportRequest(BaseModel):
    indices: list[int] | None = None


class JobCreateRequest(BaseModel):
    job_type: str = Field(min_length=1, max_length=64)
    capability: str = Field(default="", max_length=128)
    input_ref: str = Field(default="", max_length=512)
    payload: dict = Field(default_factory=dict)
    model_hint: str = Field(default="", max_length=128)
    timeout_seconds: int = Field(default=900, ge=1, le=86400)


class JobClaimRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)


class JobHeartbeatRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)


class AiJobReportRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    status: str = Field(pattern=r"^(completed|failed|cancelled)$")
    summary: str = Field(default="", max_length=10000)
    result: dict = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    model_name: str = ""
    error_message: str = ""


def _project_id(current: CurrentUser) -> int:
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


def _agent_identity(
    body_agent_id: str,
    x_ai_agent_token: str | None,
    current: CurrentUser,
    db: Session,
) -> tuple[str, int]:
    """Agent token 优先；无 token 时回退到登录用户（人工调试用）。"""
    if x_ai_agent_token:
        token = ai_agent_service.verify_agent_token(db, x_ai_agent_token)
        if token is None:
            raise HTTPException(401, "无效或已撤销的 AI Agent Token")
        if token.agent_id != body_agent_id:
            raise HTTPException(403, "Agent Token 与 agent_id 不匹配")
        return token.agent_id, token.project_id
    return body_agent_id, _project_id(current)


def _job_dict(job) -> dict:
    import json

    def _loads(raw: str, fallback):
        try:
            return json.loads(raw) if raw else fallback
        except Exception:  # noqa: BLE001 - 历史脏数据不应打断列表
            return fallback

    return {
        "id": job.id,
        "project_id": job.project_id,
        "job_type": job.job_type,
        "status": job.status,
        "capability": job.capability,
        "input_ref": job.input_ref,
        "model_hint": job.model_hint,
        "agent_id": job.agent_id,
        "model_name": job.model_name or "",
        "summary": job.summary or "",
        "payload": _loads(job.result_json, {}),
        "evidence_refs": _loads(job.evidence_refs_json, []),
        "error_message": job.error_message or "",
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.post("/agents/register", response_model=R[dict], summary="注册本地 AI Agent（签发一次性 token）")
def register_agent(
    body: AgentRegisterRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    row, plain = ai_agent_service.register_agent(
        db, body.agent_id, _project_id(current), body.capabilities
    )
    return R.ok(
        {
            "agent_id": row.agent_id,
            "status": row.status,
            "project_scope": row.project_scope,
            "token": plain,
            "token_notice": "token 仅本次返回，请立即保存到本地配置",
        }
    )


@router.post("/agents/tokens/revoke", response_model=R[dict], summary="吊销 Agent Token")
def revoke_agent_token(
    body: AgentTokenRevokeRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    ok = ai_agent_service.revoke_agent_token(db, body.token_id, _project_id(current))
    if not ok:
        raise HTTPException(404, "Token 不存在或不属于当前项目")
    return R.ok({"token_id": body.token_id, "enabled": False})


@router.post("/jobs", response_model=R[dict], summary="创建 AI Job（平台侧只派发，不推理）")
def create_job(
    body: JobCreateRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    job = ai_agent_service.create_job(
        db,
        project_id=_project_id(current),
        job_type=body.job_type,
        capability=body.capability,
        input_ref=body.input_ref,
        payload=body.payload,
        model_hint=body.model_hint,
        timeout_seconds=body.timeout_seconds,
        created_by=current.user.id,
    )
    return R.ok(_job_dict(job))


@router.get("/jobs", response_model=R[dict], summary="AI Job 列表")
def list_jobs(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    rows, total = ai_agent_service.list_jobs(
        db, project_id=_project_id(current), status=status, page=page, page_size=page_size
    )
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": [_job_dict(r) for r in rows]})


@router.get("/jobs/{job_id}", response_model=R[dict], summary="AI Job 详情（含结果）")
def get_job(
    job_id: int,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    job = ai_agent_service.get_job(db, project_id=_project_id(current), job_id=job_id)
    if job is None:
        return R(code=404, msg="AI Job 不存在")
    return R.ok(_job_dict(job))


@router.post("/jobs/claim", response_model=R[dict], summary="Agent 认领任务")
def claim_job(
    body: JobClaimRequest,
    x_ai_agent_token: str | None = Header(default=None, alias="X-AI-Agent-Token"),
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    agent_id, project_id = _agent_identity(body.agent_id, x_ai_agent_token, current, db)
    job = ai_agent_service.claim_job(db, agent_id, body.capabilities, project_id=project_id)
    return R.ok({"claimed": job is not None, "job": _job_dict(job) if job else None})


@router.post("/jobs/{job_id}/heartbeat", response_model=R[dict], summary="Agent 心跳")
def heartbeat_job(
    job_id: int,
    body: JobHeartbeatRequest,
    x_ai_agent_token: str | None = Header(default=None, alias="X-AI-Agent-Token"),
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    agent_id, _ = _agent_identity(body.agent_id, x_ai_agent_token, current, db)
    if not ai_agent_service.heartbeat_job(db, job_id, agent_id):
        raise HTTPException(409, "AI Job 未被该 Agent 持有")
    return R.ok({"job_id": job_id, "heartbeat": True})


@router.post("/jobs/{job_id}/report", response_model=R[dict], summary="Agent 上报结果")
def report_job(
    job_id: int,
    body: AiJobReportRequest,
    x_ai_agent_token: str | None = Header(default=None, alias="X-AI-Agent-Token"),
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    agent_id, _ = _agent_identity(body.agent_id, x_ai_agent_token, current, db)
    job = ai_agent_service.report_job(
        db,
        job_id,
        agent_id,
        body.status,
        body.summary,
        body.result,
        body.evidence_refs,
        body.model_name,
        body.error_message,
    )
    if job is None:
        raise HTTPException(409, "AI Job 未被该 Agent 持有或状态不允许上报")
    return R.ok(_job_dict(job))


@router.post("/jobs/{job_id}/import", response_model=R[dict], summary="把结果导入用例库")
def import_job_result(
    job_id: int,
    body: JobImportRequest | None = None,
    current: CurrentUser = Depends(require_permission("requirement:import")),
    db: Session = Depends(get_db),
):
    result = ai_agent_service.import_job_result(
        db,
        project_id=_project_id(current),
        job_id=job_id,
        user_id=current.user.id,
        indices=(body.indices if body else None),
    )
    return R.ok(result)


@router.get("/agents/health", response_model=R[dict], summary="Agent 在线状态")
def agent_health(
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    rows = ai_agent_service.health_agents(db, project_id=_project_id(current))
    return R.ok(
        {
            "online": len(rows),
            "items": [
                {
                    "agent_id": r.agent_id,
                    "project_scope": r.project_scope,
                    "last_health_at": r.last_health_at.isoformat() if r.last_health_at else None,
                }
                for r in rows
            ],
        }
    )
