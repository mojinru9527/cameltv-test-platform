"""M3 / TA-019：Agent 编排 + 执行记录（成功/失败都落 agent_executions）。"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.aiqe.agents.base import BaseAgent
from app.aiqe.models.agent import AgentExecution


def run_agent(
    db: Session,
    agent: BaseAgent,
    *,
    project_id: int,
    input_text: str,
    run_id: str | None = None,
) -> dict:
    started = datetime.now(UTC)
    row = AgentExecution(
        project_id=project_id,
        run_id=run_id,
        agent_key=agent.key,
        status="running",
        model=agent.model,
        input_text=input_text[:8000],
        started_at=started,
    )
    db.add(row)
    db.flush()
    try:
        output = agent.run(input_text)
    except Exception as exc:
        row.status = "failed"
        row.error_text = f"{type(exc).__name__}: {exc}"[:2000]
        row.finished_at = datetime.now(UTC)
        db.flush()
        raise
    row.status = "succeeded"
    row.output_json = output
    row.finished_at = datetime.now(UTC)
    db.flush()
    return output
