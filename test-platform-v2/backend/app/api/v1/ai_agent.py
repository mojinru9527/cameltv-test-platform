from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import ai_agent_service

router = APIRouter(prefix="/ai", tags=["AI Agent"])


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)


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


@router.post("/agents/register", response_model=R[dict])
def register_agent(
    body: AgentRegisterRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    row = ai_agent_service.register_agent(db, body.agent_id, current.project_id or 0, body.capabilities)
    return R.ok({"agent_id": row.agent_id, "status": row.status, "project_scope": row.project_scope})


@router.post("/jobs/claim", response_model=R[dict])
def claim_job(
    body: JobClaimRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    job = ai_agent_service.claim_job(db, body.agent_id, body.capabilities)
    return R.ok(
        {
            "claimed": job is not None,
            "job": None
            if job is None
            else {
                "id": job.id,
                "job_type": job.job_type,
                "input_ref": job.input_ref,
                "capability": job.capability,
                "model_hint": job.model_hint,
            },
        }
    )


@router.post("/jobs/{job_id}/heartbeat", response_model=R[dict])
def heartbeat_job(
    job_id: int,
    body: JobHeartbeatRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    if not ai_agent_service.heartbeat_job(db, job_id, body.agent_id):
        raise HTTPException(409, "AI Job 未被该 Agent 持有")
    return R.ok({"job_id": job_id, "heartbeat": True})


@router.post("/jobs/{job_id}/report", response_model=R[dict])
def report_job(
    job_id: int,
    body: AiJobReportRequest,
    current: CurrentUser = Depends(require_permission("apitest:execute")),
    db: Session = Depends(get_db),
):
    job = ai_agent_service.report_job(
        db,
        job_id,
        body.agent_id,
        body.status,
        body.summary,
        body.result,
        body.evidence_refs,
        body.model_name,
        body.error_message,
    )
    if job is None:
        raise HTTPException(409, "AI Job 未被该 Agent 持有或状态不允许上报")
    return R.ok({"id": job.id, "status": job.status})


@router.get("/agents/health", response_model=R[dict])
def agent_health(current: CurrentUser = Depends(require_permission("apitest:execute")), db: Session = Depends(get_db)):
    rows = ai_agent_service.health_agents(db)
    return R.ok(
        {"online": len(rows), "items": [{"agent_id": r.agent_id, "project_scope": r.project_scope} for r in rows]}
    )
