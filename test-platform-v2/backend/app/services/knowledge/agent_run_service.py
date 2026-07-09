"""Agent 执行记录服务 —— 列表/详情（读）+ start/finish 辅助（供 M4 Agent 复用）。

本期（M0）仅建立可追踪基础设施：每次 Agent 运行都能查到输入/检索上下文/输出/状态/错误。
真正的 Agent 编排在 M4 落地。写辅助函数只 `db.flush()`，由调用方 commit。
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge import AgentRun


def list_runs(
    db: Session,
    project_id: int,
    *,
    agent_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AgentRun], int]:
    stmt = select(AgentRun).where(AgentRun.project_id == project_id)
    cnt = select(func.count(AgentRun.id)).where(AgentRun.project_id == project_id)
    if agent_type:
        stmt = stmt.where(AgentRun.agent_type == agent_type)
        cnt = cnt.where(AgentRun.agent_type == agent_type)
    if status:
        stmt = stmt.where(AgentRun.status == status)
        cnt = cnt.where(AgentRun.status == status)

    total = db.scalar(cnt) or 0
    page_size = max(1, min(page_size, 200))
    rows = list(
        db.scalars(
            stmt.order_by(AgentRun.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, total


def get_run(db: Session, run_id: int, project_id: int) -> AgentRun | None:
    row = db.get(AgentRun, run_id)
    if not row or row.project_id != project_id:
        return None
    return row


# ── 供 M4 Agent 编排复用的辅助 ──

def start_run(
    db: Session,
    *,
    project_id: int,
    agent_type: str,
    trigger_type: str = "manual",
    input_data: dict | None = None,
    operator_id: int = 0,
) -> AgentRun:
    run = AgentRun(
        project_id=project_id,
        agent_type=agent_type,
        trigger_type=trigger_type,
        input_json=json.dumps(input_data or {}, ensure_ascii=False),
        status="running",
        operator_id=operator_id,
    )
    db.add(run)
    db.flush()
    return run


def finish_run(
    db: Session,
    run: AgentRun,
    *,
    status: str = "success",
    output_data: dict | None = None,
    retrieved_context: dict | None = None,
    error_message: str = "",
    duration_ms: int = 0,
) -> AgentRun:
    run.status = status
    if output_data is not None:
        run.output_json = json.dumps(output_data, ensure_ascii=False)
    if retrieved_context is not None:
        run.retrieved_context_json = json.dumps(retrieved_context, ensure_ascii=False)
    run.error_message = error_message
    run.duration_ms = duration_ms
    run.finished_at = datetime.now()
    db.flush()
    return run
