"""M6 / TA-033：Reliability + Security Hardening。

- Worker 被强杀：Run 受控失败（COMPLETED/INCOMPLETE），未完成节点 BLOCKED，重复恢复幂等；
- 幂等变更账本：同一 key 只执行一次，防重复扣款/造数；
- RBAC 拒绝审计：权限拒绝必须写审计。
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.hardening import MutationLedger
from app.aiqe.models.run import TestRun
from app.aiqe.services.run_state import TERMINAL_STATUSES, apply_transition
from app.services import audit_service

ORPHAN_NODE_STATUSES = ("PENDING", "READY", "RUNNING")


class HardeningError(ValueError):
    pass


def recover_after_worker_kill(
    db: Session, run_id: str, *, reason: str = "worker killed"
) -> dict[str, Any]:
    run = db.get(TestRun, run_id)
    if run is None:
        raise HardeningError(f"Run 不存在: {run_id}")
    if run.status in TERMINAL_STATUSES:
        return {"run_id": run_id, "recovered": False, "status": run.status, "blocked_nodes": 0}

    blocked = 0
    now = datetime.now(UTC)
    for node in run.node_runs:
        if node.status in ORPHAN_NODE_STATUSES:
            node.status = "BLOCKED"
            node.error_class = "WORKER_LOST"
            node.finished_at = now
            blocked += 1

    if run.status == "RUNNING":
        apply_transition(run, "COMPLETED", outcome="INCOMPLETE")
    else:
        apply_transition(run, "ERROR")
    run.finished_at = now
    db.flush()
    return {
        "run_id": run_id,
        "recovered": True,
        "status": run.status,
        "outcome": run.outcome,
        "blocked_nodes": blocked,
    }


def run_idempotent_mutation(
    db: Session,
    key: str,
    mutation: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any] | None, bool]:
    """同一 key 只执行一次；返回 (结果, 是否首次执行)。"""
    if not str(key).strip():
        raise HardeningError("幂等 key 不能为空")
    existing = db.scalar(select(MutationLedger).where(MutationLedger.key == key))
    if existing is not None:
        return existing.result_json, False
    result = mutation()
    row = MutationLedger(key=str(key), result_json=result)
    db.add(row)
    db.flush()
    return result, True


def audit_permission_denied(
    db: Session,
    *,
    user_id: int,
    username: str,
    project_id: int,
    action: str,
    target: str,
    ip: str = "",
) -> None:
    audit_service.write_audit(
        db,
        user_id=user_id,
        username=username,
        project_id=project_id,
        action=action,
        target=target,
        detail="permission_denied",
        ip=ip,
    )
    db.commit()
