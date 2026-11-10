"""M2 / TA-010：DAG 调度器（13 号 §6.3）。

职责：把 Workflow graph 实例化为 NodeRun，按 depends_on 推进 READY，
限制并行度，失败阻断（fail_fast / 依赖传播），终态收口 Run，并支持 Worker 重启恢复。

不负责真正执行节点：dispatch 回调由调用方接到 execution_jobs / worker。
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.workflow import ResourceLock
from app.aiqe.services import resource_lock
from app.aiqe.services.run_state import apply_transition

NODE_TERMINAL = frozenset({"PASSED", "FAILED", "BLOCKED", "SKIPPED", "CANCELED", "ERROR"})
NODE_FAILED = frozenset({"FAILED", "ERROR", "TIMED_OUT"})
ACTIVE_NODE = frozenset({"READY", "RUNNING"})

Dispatch = Callable[[NodeRun], None]


def _node_defs(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["key"]: node for node in graph.get("nodes", [])}


def _deps(graph: dict[str, Any]) -> dict[str, list[str]]:
    return {
        node["key"]: [str(dep) for dep in (node.get("depends_on") or [])]
        for node in graph.get("nodes", [])
    }


def _policy(graph: dict[str, Any]) -> tuple[int, bool, str | None]:
    policy = graph.get("run_policy") or {}
    try:
        parallel = max(1, int(policy.get("max_parallel_nodes", 3)))
    except (TypeError, ValueError):
        parallel = 3
    cleanup = policy.get("cleanup_node")
    return parallel, bool(policy.get("fail_fast", False)), cleanup


def create_node_runs(db: Session, run_id: str, graph: dict[str, Any]) -> list[NodeRun]:
    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))
    existing = {row.node_key: row for row in rows}
    for node in graph.get("nodes", []):
        key = node["key"]
        if key in existing:
            continue
        row = NodeRun(
            run_id=run_id,
            node_key=key,
            driver_key=str(node.get("driver") or ""),
            status="PENDING",
            input_ref=node.get("input") or {},
            resource_keys_json=node.get("resource_keys") or [],
        )
        db.add(row)
        existing[key] = row
    db.flush()
    return list(existing.values())


def _satisfied(
    key: str,
    defs: dict[str, dict[str, Any]],
    deps: dict[str, list[str]],
    statuses: dict[str, str],
    cleanup: str | None,
) -> bool:
    node = defs[key]
    if node.get("type") == "cleanup" or node.get("depends_on_terminal") or key == cleanup:
        return all(
            statuses.get(other, "PENDING") in NODE_TERMINAL
            for other in defs
            if other != key
        )
    return all(statuses.get(dep, "PENDING") == "PASSED" for dep in deps.get(key, []))


def _block_downstream(
    key: str, deps: dict[str, list[str]], rows: dict[str, NodeRun], skip: set[str]
) -> None:
    for other, other_deps in deps.items():
        if key in other_deps and other not in skip:
            row = rows.get(other)
            if row is not None and row.status not in NODE_TERMINAL:
                row.status = "BLOCKED"
                skip.add(other)
                _block_downstream(other, deps, rows, skip)


def _finalize(db: Session, run: TestRun, rows: list[NodeRun], graph: dict[str, Any]) -> None:
    if run.status in {"COMPLETED", "BLOCKED", "CANCELED", "ERROR"}:
        return
    if any(row.status not in NODE_TERMINAL for row in rows):
        return
    if run.status != "RUNNING":
        return
    statuses = {row.node_key: row.status for row in rows}
    if any(status in NODE_FAILED for status in statuses.values()):
        apply_transition(run, "COMPLETED", outcome="FAIL")
    elif any(status == "BLOCKED" for status in statuses.values()):
        apply_transition(run, "COMPLETED", outcome="INCOMPLETE")
    else:
        apply_transition(run, "COMPLETED", outcome="PASS")
    run.finished_at = datetime.now(UTC)


def schedule(
    db: Session,
    run_id: str,
    graph: dict[str, Any],
    *,
    dispatch: Dispatch | None = None,
    ttl_seconds: int = 60,
) -> list[NodeRun]:
    run = db.scalar(select(TestRun).where(TestRun.id == run_id).with_for_update())
    if run is None:
        raise LookupError(run_id)
    if run.status == "QUEUED":
        apply_transition(run, "RUNNING")
        run.started_at = run.started_at or datetime.now(UTC)
    elif run.status != "RUNNING":
        return list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))

    rows = create_node_runs(db, run_id, graph)
    by_key = {row.node_key: row for row in rows}
    defs = _node_defs(graph)
    deps = _deps(graph)
    parallel, _fail_fast, cleanup = _policy(graph)

    progressed = True
    while progressed:
        progressed = False
        statuses = {row.node_key: row.status for row in rows}
        active = sum(1 for row in rows if row.status in ACTIVE_NODE)
        for key, row in by_key.items():
            if active >= parallel:
                break
            if row.status != "PENDING":
                continue
            if not _satisfied(key, defs, deps, statuses, cleanup):
                continue
            acquired: list[tuple[str, int]] = []
            try:
                for resource in row.resource_keys_json or []:
                    acquired.append(
                        (
                            resource,
                            resource_lock.acquire(
                                db,
                                str(resource),
                                f"{run_id}:{key}",
                                ttl_seconds=ttl_seconds,
                            ),
                        )
                    )
            except resource_lock.LockUnavailable:
                for resource, token in acquired:
                    resource_lock.release(db, resource, token)
                continue
            row.status = "READY"
            row.attempt_count = int(row.attempt_count or 0) + 1
            statuses[key] = "READY"
            active += 1
            progressed = True
            if dispatch is not None:
                dispatch(row)

    _finalize(db, run, rows, graph)
    db.flush()
    return rows


def mark_running(db: Session, run_id: str, node_key: str) -> NodeRun:
    row = db.scalar(
        select(NodeRun).where(NodeRun.run_id == run_id, NodeRun.node_key == node_key)
    )
    if row is None:
        raise LookupError(node_key)
    if row.status == "READY":
        row.status = "RUNNING"
        row.started_at = row.started_at or datetime.now(UTC)
        db.flush()
    return row


def complete_node(
    db: Session,
    run_id: str,
    node_key: str,
    status: str,
    graph: dict[str, Any],
    *,
    error_class: str | None = None,
    outputs: Mapping[str, Any] | None = None,
) -> TestRun:
    if status not in NODE_TERMINAL:
        raise ValueError(f"非法节点终态: {status}")
    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))
    by_key = {row.node_key: row for row in rows}
    row = by_key.get(node_key)
    if row is None:
        raise LookupError(node_key)
    row.status = status
    row.finished_at = datetime.now(UTC)
    if error_class:
        row.error_class = error_class
    if outputs:
        row.output_ref = {**(row.output_ref or {}), **dict(outputs)}

    for resource in row.resource_keys_json or []:
        try:
            token = resource_lock.acquire(
                db, str(resource), f"{run_id}:{node_key}", ttl_seconds=1
            )
            resource_lock.release(db, str(resource), token)
        except resource_lock.LockUnavailable:
            pass

    run = db.scalar(select(TestRun).where(TestRun.id == run_id).with_for_update())
    if run is None:
        raise LookupError(run_id)

    deps = _deps(graph)
    _parallel, fail_fast, _cleanup = _policy(graph)

    if status in NODE_FAILED and fail_fast:
        for other in rows:
            if other.status not in NODE_TERMINAL:
                other.status = "BLOCKED"
        if run.status == "RUNNING":
            apply_transition(run, "BLOCKED")
        run.finished_at = datetime.now(UTC)
        db.flush()
        return run

    if status in NODE_FAILED:
        _block_downstream(node_key, deps, by_key, {node_key})

    _finalize(db, run, rows, graph)
    db.flush()
    return run


def recover(
    db: Session,
    run_id: str,
    graph: dict[str, Any],
    *,
    dispatch: Dispatch | None = None,
) -> list[NodeRun]:
    """Worker 重启恢复：RUNNING 节点若锁已过期/丢失 → 回到 PENDING 重新调度。"""
    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))
    now = datetime.now(UTC)
    for row in rows:
        if row.status != "RUNNING":
            continue
        owner = f"{run_id}:{row.node_key}"
        live = False
        for resource in row.resource_keys_json or []:
            lock = db.get(ResourceLock, str(resource))
            if lock is None or lock.owner_id != owner:
                continue
            expires = lock.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires > now:
                live = True
                break
        if not live:
            row.status = "PENDING"
    db.flush()
    return schedule(db, run_id, graph, dispatch=dispatch)
