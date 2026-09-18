"""ExecutionJob 控制面服务（Batch 258 / B1-4）。

控制面职责：登记任务、按项目派发给本地节点、收租约心跳、回收失联租约、保存结果与证据引用。
**不执行**任何浏览器/模型动作（ADR-0026）。
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import APIException
from app.models.ai_job import AiAgent
from app.models.execution_job import ExecutionJob

JOB_KINDS = frozenset({"api", "web"})
REPORT_STATUSES = frozenset({"completed", "failed", "cancelled"})


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _loads(raw: str | None, fallback):
    try:
        return json.loads(raw) if raw else fallback
    except (json.JSONDecodeError, TypeError):
        return fallback


def job_dict(job: ExecutionJob) -> dict:
    return {
        "id": job.id,
        "project_id": job.project_id,
        "kind": job.kind,
        "status": job.status,
        "case_refs": _loads(job.case_refs_json, []),
        "env_ref": job.env_ref or "",
        "attempt": job.attempt,
        "node_id": job.node_id or "",
        "evidence_bundle_id": job.evidence_bundle_id,
        "summary": job.summary or "",
        "result": _loads(job.result_json, {}),
        "error_message": job.error_message or "",
        "claimed_at": job.claimed_at.isoformat() if job.claimed_at else None,
        "lease_expires_at": job.lease_expires_at.isoformat() if job.lease_expires_at else None,
        "heartbeat_at": job.heartbeat_at.isoformat() if job.heartbeat_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


def _lease_ttl() -> timedelta:
    return timedelta(seconds=max(1, int(settings.execution_job_lease_seconds)))


def _node_capabilities(agent: AiAgent) -> list[str]:
    caps = _loads(agent.capabilities_json, [])
    return [str(cap) for cap in caps] if isinstance(caps, list) else []


# ── 任务生产端 ─────────────────────────────────────────────────

def create_job(
    db: Session,
    *,
    project_id: int,
    kind: str,
    case_refs: list[str],
    env_ref: str = "",
    timeout_seconds: int = 1800,
) -> ExecutionJob:
    if kind not in JOB_KINDS:
        raise APIException(
            code=400, msg=f"不支持的执行类型: {kind}（仅支持 {'/'.join(sorted(JOB_KINDS))}）",
            http_status=400,
        )
    job = ExecutionJob(
        project_id=project_id,
        kind=kind,
        status="pending",
        case_refs_json=json.dumps(list(case_refs or []), ensure_ascii=False),
        env_ref=(env_ref or "")[:255],
        attempt=0,
        timeout_seconds=max(1, int(timeout_seconds)),
        node_id="",
        result_json="{}",
        summary="",
        error_message="",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_jobs(
    db: Session,
    *,
    project_id: int,
    status: str | None = None,
    kind: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ExecutionJob], int]:
    where = [ExecutionJob.project_id == project_id]
    if status:
        where.append(ExecutionJob.status == status)
    if kind:
        where.append(ExecutionJob.kind == kind)
    total = db.scalar(select(func.count()).select_from(ExecutionJob).where(*where)) or 0
    rows = db.scalars(
        select(ExecutionJob)
        .where(*where)
        .order_by(ExecutionJob.id.desc())
        .offset(max(0, (page - 1) * page_size))
        .limit(page_size)
    ).all()
    return list(rows), int(total)


def get_job(db: Session, *, project_id: int, job_id: int) -> ExecutionJob | None:
    return db.scalar(
        select(ExecutionJob).where(
            ExecutionJob.id == job_id, ExecutionJob.project_id == project_id
        )
    )


# ── 认领 / 心跳 / 上报 / 回收 ──────────────────────────────────

def reclaim_stale(db: Session, *, now_ts: datetime | None = None) -> int:
    """把租约过期的 running 任务放回 pending（断线不丢任务）。"""
    current = now_ts or now()
    reclaimed = 0
    rows = db.scalars(select(ExecutionJob).where(ExecutionJob.status == "running")).all()
    for job in rows:
        deadline = job.lease_expires_at
        if deadline is None:
            # 历史/异常数据没有租约字段：退回心跳推算，避免任务永久卡死
            anchor = job.heartbeat_at or job.claimed_at or job.started_at
            deadline = anchor + _lease_ttl() if anchor else None
        if deadline is None or deadline <= current:
            job.status = "pending"
            job.node_id = ""
            job.claimed_at = None
            job.lease_expires_at = None
            job.heartbeat_at = None
            job.error_message = "reclaimed: node lease expired"
            reclaimed += 1
    if reclaimed:
        db.commit()
    return reclaimed


def claim_job(db: Session, *, node_id: str, project_id: int) -> ExecutionJob | None:
    """节点认领本项目任务。节点必须已注册且在线；`kind` 必须在其能力声明内。"""
    agent = db.scalar(
        select(AiAgent).where(AiAgent.agent_id == node_id, AiAgent.status == "online")
    )
    if agent is None:
        raise APIException(code=404, msg="执行节点未注册或离线", http_status=404)
    reclaim_stale(db)
    capabilities = _node_capabilities(agent)
    rows = db.scalars(
        select(ExecutionJob)
        .where(ExecutionJob.status == "pending", ExecutionJob.project_id == project_id)
        .order_by(ExecutionJob.id.asc())
        .with_for_update(skip_locked=True)
    ).all()
    for job in rows:
        if capabilities and job.kind not in capabilities:
            continue
        current = now()
        job.status = "running"
        job.node_id = node_id
        job.claimed_at = current
        job.heartbeat_at = current
        job.lease_expires_at = current + _lease_ttl()
        job.started_at = job.started_at or current
        job.attempt = int(job.attempt or 0) + 1
        job.error_message = ""
        db.commit()
        db.refresh(job)
        return job
    return None


def heartbeat(db: Session, *, job_id: int, node_id: str) -> bool:
    job = db.scalar(
        select(ExecutionJob).where(
            ExecutionJob.id == job_id,
            ExecutionJob.node_id == node_id,
            ExecutionJob.status == "running",
        )
    )
    if job is None:
        return False
    current = now()
    job.heartbeat_at = current
    job.lease_expires_at = current + _lease_ttl()
    db.commit()
    return True


def report(
    db: Session,
    *,
    job_id: int,
    node_id: str,
    status: str,
    summary: str = "",
    result: dict | None = None,
    evidence_bundle_id: int | None = None,
    error_message: str = "",
) -> ExecutionJob | None:
    if status not in REPORT_STATUSES:
        raise APIException(
            code=400, msg=f"上报状态非法: {status}", http_status=400
        )
    job = db.scalar(
        select(ExecutionJob).where(
            ExecutionJob.id == job_id,
            ExecutionJob.node_id == node_id,
            ExecutionJob.status == "running",
        )
    )
    if job is None:
        return None
    job.status = status
    job.summary = summary or ""
    job.result_json = json.dumps(result or {}, ensure_ascii=False, default=str)
    job.error_message = error_message or ""
    job.evidence_bundle_id = evidence_bundle_id
    job.finished_at = now()
    job.lease_expires_at = None
    db.commit()
    db.refresh(job)
    return job


# ── 节点与队列状态（B1-6 的数据源）──────────────────────────────

def node_status(db: Session, *, project_id: int) -> dict:
    online_nodes = db.scalar(
        select(func.count())
        .select_from(AiAgent)
        .where(AiAgent.status == "online", AiAgent.project_scope == project_id)
    ) or 0
    pending = db.scalar(
        select(func.count())
        .select_from(ExecutionJob)
        .where(ExecutionJob.project_id == project_id, ExecutionJob.status == "pending")
    ) or 0
    running = db.scalar(
        select(func.count())
        .select_from(ExecutionJob)
        .where(ExecutionJob.project_id == project_id, ExecutionJob.status == "running")
    ) or 0
    stalled = db.scalar(
        select(func.count())
        .select_from(ExecutionJob)
        .where(
            ExecutionJob.project_id == project_id,
            ExecutionJob.status == "running",
            or_(
                ExecutionJob.lease_expires_at.is_(None),
                ExecutionJob.lease_expires_at <= now(),
            ),
        )
    ) or 0
    return {
        "online_nodes": int(online_nodes),
        "queue_length": int(pending),
        "running_jobs": int(running),
        "stalled_jobs": int(stalled),
    }


def list_nodes(db: Session, *, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(AiAgent).where(AiAgent.project_scope == project_id).order_by(AiAgent.id.asc())
    ).all()
    return [
        {
            "node_id": agent.agent_id,
            "status": agent.status,
            "capabilities": _node_capabilities(agent),
            "last_health_at": agent.last_health_at.isoformat() if agent.last_health_at else None,
        }
        for agent in rows
    ]
