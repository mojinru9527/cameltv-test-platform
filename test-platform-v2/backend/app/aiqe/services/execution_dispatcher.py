"""P0：把 AIQE NodeRun 桥接到既有 ExecutionJob/Worker 队列。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.models.execution_job import ExecutionJob


class DispatchError(ValueError):
    pass


def enqueue_node_run(
    db: Session,
    node_run: NodeRun,
    *,
    kind: str = "api",
    timeout_seconds: int = 1800,
    graph: dict | None = None,
) -> ExecutionJob:
    if node_run.execution_job_id:
        existing = db.get(ExecutionJob, node_run.execution_job_id)
        if existing is not None:
            return existing
    run = db.get(TestRun, node_run.run_id)
    if run is None:
        raise DispatchError(f"Run 不存在: {node_run.run_id}")
    job = ExecutionJob(
        project_id=run.project_id,
        kind=kind,
        status="pending",
        case_refs_json=json.dumps([node_run.node_key]),
        payload_json=json.dumps(
            {
                "run_id": node_run.run_id,
                "node_run_id": node_run.id,
                "node_key": node_run.node_key,
                **({"graph": graph} if graph else {}),
            }
        ),
        env_ref=str(run.environment_id or ""),
        timeout_seconds=timeout_seconds,
    )
    db.add(job)
    db.flush()
    node_run.execution_job_id = job.id
    db.flush()
    return job
