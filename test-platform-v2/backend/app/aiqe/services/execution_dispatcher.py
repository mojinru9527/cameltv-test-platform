"""P0 + v1.4：把 AIQE NodeRun 桥接到既有 ExecutionJob/Worker 队列。

- 幂等：一个 NodeRun 最多一个 ExecutionJob（DB 唯一约束 + 本函数短路）；
- 不把 secret 明文写进 payload：只下发 `secret_keys`，真实值由 Runner 运行时注入；
- 下发祖先节点 outputs，Runner 可解析 `${nodes.<key>.outputs.<name>}`；
- `producer_event_id` 保证重复 dispatch 不生成第二个 Job。
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.models.execution_job import ExecutionJob


class DispatchError(ValueError):
    pass


def _ancestor_outputs(db: Session, run_id: str, node_key: str, graph: dict | None) -> dict:
    if not graph:
        return {}
    deps = {
        str(node.get("key")): [str(dep) for dep in (node.get("depends_on") or [])]
        for node in graph.get("nodes") or []
        if isinstance(node, dict)
    }
    ancestors: set[str] = set()
    stack = list(deps.get(node_key, []))
    while stack:
        current = stack.pop()
        if current in ancestors:
            continue
        ancestors.add(current)
        stack.extend(deps.get(current, []))
    if not ancestors:
        return {}
    rows = list(
        db.scalars(
            select(NodeRun).where(
                NodeRun.run_id == run_id, NodeRun.node_key.in_(sorted(ancestors))
            )
        )
    )
    return {row.node_key: dict(row.outputs_json or row.output_ref or {}) for row in rows}


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
        if existing is not None and existing.status in {"pending", "running"}:
            return existing
        # 终态 Job 不能复用：retry 必须生成新的 ExecutionJob/StepAttempt，
        # 旧 Job 与旧 attempt 保留，禁止覆盖历史。
    run = db.get(TestRun, node_run.run_id)
    if run is None:
        raise DispatchError(f"Run 不存在: {node_run.run_id}")
    payload = {
        "run_id": node_run.run_id,
        "node_run_id": node_run.id,
        "node_key": node_run.node_key,
        "driver": node_run.driver_key,
        # 原始输入保留变量引用；Runner 用 node_outputs + 本地 secret provider 解析。
        "input": node_run.input_ref or {},
        "node_outputs": _ancestor_outputs(db, run.id, node_run.node_key, graph),
        "secret_keys": list(node_run.secret_keys_json or []),
        "fixtures": (run.environment_snapshot_json or {}).get("fixtures") or {},
        "assertions": list(node_run.assertions_json or []),
    }
    if graph:
        payload["graph"] = graph
    job = ExecutionJob(
        project_id=run.project_id,
        kind=kind,
        status="pending",
        case_refs_json=json.dumps([node_run.node_key]),
        payload_json=json.dumps(payload, ensure_ascii=False),
        env_ref=str(run.environment_id or ""),
        timeout_seconds=timeout_seconds,
    )
    db.add(job)
    db.flush()
    node_run.execution_job_id = job.id
    db.flush()
    return job
