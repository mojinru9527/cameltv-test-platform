from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.ai_job import AiAgent, AiJob, AiResult


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def register_agent(db: Session, agent_id: str, project_scope: int, capabilities: list[str]) -> AiAgent:
    row = db.scalar(select(AiAgent).where(AiAgent.agent_id == agent_id))
    if row is None:
        row = AiAgent(agent_id=agent_id)
        db.add(row)
    row.project_scope = project_scope
    row.capabilities_json = json.dumps(capabilities, ensure_ascii=False)
    row.status = "online"
    row.last_health_at = _now()
    db.commit()
    db.refresh(row)
    return row


def claim_job(db: Session, agent_id: str, capabilities: list[str]):
    agent = db.scalar(select(AiAgent).where(AiAgent.agent_id == agent_id, AiAgent.status == "online"))
    if agent is None:
        raise APIException(code=404, msg="AI Agent 未注册或离线", http_status=404)
    rows = db.scalars(
        select(AiJob).where(AiJob.status == "pending").order_by(AiJob.id.asc()).with_for_update(skip_locked=True)
    ).all()
    for job in rows:
        if job.capability and job.capability not in capabilities:
            continue
        now = _now()
        job.status = "running"
        job.agent_id = agent_id
        job.locked_at = now
        job.heartbeat_at = now
        job.started_at = job.started_at or now
        db.commit()
        db.refresh(job)
        return job
    return None


def heartbeat_job(db: Session, job_id: int, agent_id: str) -> bool:
    job = db.scalar(select(AiJob).where(AiJob.id == job_id, AiJob.agent_id == agent_id, AiJob.status == "running"))
    if job is None:
        return False
    job.heartbeat_at = _now()
    job.locked_at = job.heartbeat_at
    db.commit()
    return True


def report_job(
    db: Session,
    job_id: int,
    agent_id: str,
    status: str,
    summary: str,
    result: dict,
    evidence_refs: list[str],
    model_name: str,
    error_message: str,
):
    if status not in {"completed", "failed", "cancelled"}:
        raise APIException(code=400, msg="AI Job report status 非法", http_status=400)
    job = db.scalar(select(AiJob).where(AiJob.id == job_id, AiJob.agent_id == agent_id, AiJob.status == "running"))
    if job is None:
        return None
    job.status = status
    job.summary = summary
    job.result_json = json.dumps(result, ensure_ascii=False, default=str)
    job.evidence_refs_json = json.dumps(evidence_refs, ensure_ascii=False)
    job.error_message = error_message
    job.finished_at = _now()
    db.add(AiResult(job_id=job.id, status=status, result_json=job.result_json, summary=summary))
    db.commit()
    db.refresh(job)
    return job


def health_agents(db: Session) -> list[AiAgent]:
    return list(db.scalars(select(AiAgent).where(AiAgent.status == "online")).all())
