"""需求域 AI 任务派发（Batch 248）。

`settings.ai_platform_inference` 为 False（默认）时，平台不再调用任何模型，
而是创建 AiJob 交由本地 AI Agent 执行；为 True 时保留旧的平台内推理链路
（仅用于运维/评估，普通用户主入口应保持关闭）。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import ai_agent_service


def local_agent_mode() -> bool:
    """平台是否把 AI 交给本地 Agent（即平台不自己推理）。"""
    return not bool(settings.ai_platform_inference)


def dispatch_requirement_job(
    db: Session,
    *,
    document_id: int,
    job_type: str,
    project_id: int,
    user_id: int,
    payload: dict | None = None,
) -> dict:
    """创建一个需求域 AiJob 并返回前端可直接展示的任务引用。"""
    body = {"document_id": document_id}
    if payload:
        body.update(payload)
    job = ai_agent_service.create_job(
        db,
        project_id=project_id,
        job_type=job_type,
        capability=job_type,
        input_ref=f"requirement:{document_id}",
        payload=body,
        created_by=user_id,
    )
    return {
        "mode": "local_agent",
        "job_id": job.id,
        "job_type": job_type,
        "document_id": document_id,
        "status": job.status,
        "message": "已提交到本地 AI Agent，请在「AI 任务」页查看结果并导入",
    }
