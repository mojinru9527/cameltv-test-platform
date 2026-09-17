"""本地 AI Agent 控制面服务（Batch 248）。

平台只做三件事：创建 AiJob、把 Job 派发给本地 Agent、接收并保存结果。
平台自身不做 LLM 推理（`settings.ai_platform_inference` 默认 False）。
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import APIException
from app.models.ai_agent_token import AiAgentToken
from app.models.ai_job import AiAgent, AiJob, AiResult

AGENT_TOKEN_PREFIX = "agt_"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


# ── Agent 注册与凭据 ────────────────────────────────────────────

def register_agent(
    db: Session,
    agent_id: str,
    project_scope: int,
    capabilities: list[str],
    *,
    issue_token: bool = True,
) -> tuple[AiAgent, str | None]:
    """注册/更新 Agent；默认签发一次性明文 token（仅本次返回）。"""
    row = db.scalar(select(AiAgent).where(AiAgent.agent_id == agent_id))
    if row is None:
        row = AiAgent(agent_id=agent_id)
        db.add(row)
    row.project_scope = project_scope
    row.capabilities_json = json.dumps(capabilities, ensure_ascii=False)
    row.status = "online"
    row.last_health_at = _now()

    plain: str | None = None
    if issue_token:
        plain = f"{AGENT_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
        db.add(
            AiAgentToken(
                project_id=project_scope,
                agent_id=agent_id,
                name=f"{agent_id}-token",
                token_hash=_hash_token(plain),
                token_prefix=plain[:12],
                enabled=True,
            )
        )
    db.commit()
    db.refresh(row)
    return row, plain


def verify_agent_token(db: Session, plain: str) -> AiAgentToken | None:
    if not plain:
        return None
    token = db.scalar(select(AiAgentToken).where(AiAgentToken.token_hash == _hash_token(plain)))
    if token is None or not token.enabled or token.revoked_at is not None:
        return None
    token.last_used_at = _now()
    db.commit()
    db.refresh(token)
    return token


def revoke_agent_token(db: Session, token_id: int, project_id: int) -> bool:
    token = db.scalar(
        select(AiAgentToken).where(AiAgentToken.id == token_id, AiAgentToken.project_id == project_id)
    )
    if token is None:
        return False
    token.enabled = False
    token.revoked_at = _now()
    db.commit()
    return True


# ── Job 生产端 ─────────────────────────────────────────────────

def create_job(
    db: Session,
    *,
    project_id: int,
    job_type: str,
    capability: str = "",
    input_ref: str = "",
    payload: dict | None = None,
    model_hint: str = "",
    timeout_seconds: int = 900,
    created_by: int = 0,
) -> AiJob:
    job = AiJob(
        project_id=project_id,
        job_type=job_type,
        status="pending",
        input_ref=input_ref,
        capability=capability or job_type,
        model_hint=model_hint,
        timeout_seconds=timeout_seconds,
        agent_id="",
        result_json=json.dumps(payload or {}, ensure_ascii=False),
        summary="",
        evidence_refs_json="[]",
        model_name="",
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
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AiJob], int]:
    where = [AiJob.project_id == project_id]
    if status:
        where.append(AiJob.status == status)
    total = db.scalar(select(func.count()).select_from(AiJob).where(*where)) or 0
    rows = db.scalars(
        select(AiJob)
        .where(*where)
        .order_by(AiJob.id.desc())
        .offset(max(0, (page - 1) * page_size))
        .limit(page_size)
    ).all()
    return list(rows), int(total)


def get_job(db: Session, *, project_id: int, job_id: int) -> AiJob | None:
    return db.scalar(select(AiJob).where(AiJob.id == job_id, AiJob.project_id == project_id))


# ── 认领 / 心跳 / 上报 ─────────────────────────────────────────

def reclaim_stale_jobs(db: Session, *, stale_seconds: int | None = None) -> int:
    """把心跳超时的 running 任务放回 pending，避免 Agent 崩溃后任务永久卡死。"""
    seconds = settings.ai_job_stale_seconds if stale_seconds is None else stale_seconds
    cutoff = _now().timestamp() - max(1, int(seconds))
    reclaimed = 0
    rows = db.scalars(select(AiJob).where(AiJob.status == "running")).all()
    for job in rows:
        heartbeat = job.heartbeat_at or job.locked_at or job.started_at
        if heartbeat is None or heartbeat.timestamp() <= cutoff:
            job.status = "pending"
            job.agent_id = ""
            job.locked_at = None
            job.heartbeat_at = None
            job.error_message = "reclaimed: agent heartbeat lost"
            reclaimed += 1
    if reclaimed:
        db.commit()
    return reclaimed


def claim_job(db: Session, agent_id: str, capabilities: list[str], *, project_id: int | None = None):
    agent = db.scalar(select(AiAgent).where(AiAgent.agent_id == agent_id, AiAgent.status == "online"))
    if agent is None:
        raise APIException(code=404, msg="AI Agent 未注册或离线", http_status=404)
    reclaim_stale_jobs(db)

    scope = project_id if project_id else (agent.project_scope or 0)
    where = [AiJob.status == "pending"]
    if scope:
        where.append(AiJob.project_id == scope)
    rows = db.scalars(
        select(AiJob).where(*where).order_by(AiJob.id.asc()).with_for_update(skip_locked=True)
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
        job.error_message = ""
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
    job.model_name = model_name or ""
    job.error_message = error_message
    job.finished_at = _now()
    db.add(AiResult(job_id=job.id, status=status, result_json=job.result_json, summary=summary))
    db.commit()
    db.refresh(job)
    return job


def health_agents(db: Session, *, project_id: int | None = None) -> list[AiAgent]:
    where = [AiAgent.status == "online"]
    if project_id:
        where.append(AiAgent.project_scope == project_id)
    return list(db.scalars(select(AiAgent).where(*where)).all())


# ── 结果导入 ───────────────────────────────────────────────────

def import_job_result(
    db: Session,
    *,
    project_id: int,
    job_id: int,
    user_id: int,
    indices: list[int] | None = None,
) -> dict:
    """把已完成 Job 的结果导入用例库（当前支持 generate 类型）。

    结果先写入需求文档的 `ai_raw`（与平台内 AI 生成结果同一落点），
    再复用 `requirement_service` 的既有导入链路，保证两条链路的用例结构一致。
    同一 Job 重复导入直接短路，避免重复用例。
    """
    from app.models.requirement import RequirementDocument
    from app.services import requirement_service

    job = get_job(db, project_id=project_id, job_id=job_id)
    if job is None:
        raise APIException(code=404, msg="AI Job 不存在", http_status=404)
    if job.status != "completed":
        raise APIException(code=400, msg="只有已完成（completed）的 AI 任务可以导入", http_status=400)
    if job.imported_at is not None:
        return {"imported": 0, "skipped": 0, "total": 0, "already_imported": True}
    if job.job_type != "generate":
        raise APIException(
            code=400,
            msg="当前仅支持 generate 类型结果的自动导入；extract 结果请在需求页人工确认",
            http_status=400,
        )

    try:
        payload = json.loads(job.result_json or "{}")
    except (json.JSONDecodeError, TypeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    document_id = int(payload.get("document_id") or 0)
    if not document_id:
        raise APIException(code=400, msg="任务结果缺少 document_id，无法定位需求文档", http_status=400)

    doc = db.scalar(
        select(RequirementDocument).where(
            RequirementDocument.id == document_id,
            RequirementDocument.project_id == project_id,
        )
    )
    if doc is None:
        raise APIException(code=404, msg="需求文档不存在或不属于当前项目", http_status=404)

    try:
        merged = json.loads(doc.ai_raw or "{}")
        if not isinstance(merged, dict):
            merged = {}
    except (json.JSONDecodeError, TypeError):
        merged = {}
    functional = payload.get("functional_cases") or []
    api_cases = payload.get("api_cases") or []
    merged["functional_cases"] = functional
    merged["api_cases"] = api_cases
    doc.ai_raw = json.dumps(merged, ensure_ascii=False)

    selected_indices = indices if indices is not None else list(range(len(functional) + len(api_cases)))
    selected = requirement_service.prepare_cases_for_import(
        db,
        doc_id=document_id,
        project_id=project_id,
        indices=selected_indices,
        edited_cases=[],
        reviewer_id=user_id,
    )
    if not selected:
        raise APIException(code=400, msg="任务结果中没有可导入的用例", http_status=400)
    result = requirement_service.import_cases(
        db,
        document_id,
        selected,
        project_id=project_id,
        commit=False,
        creator_id=user_id,
    )
    job.imported_at = _now()
    db.commit()
    return {
        "imported": int(result.get("imported", 0)),
        "skipped": int(result.get("skipped", 0)),
        "total": len(selected),
        "already_imported": False,
    }
