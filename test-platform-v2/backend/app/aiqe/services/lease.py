"""AUD-006：租约与 fencing（旧 Worker 迟到结果必须被拒绝）。

v1.5 §01 AUD-006 技术机制 1–2：

- Job claim 使用原子 UPDATE + lease expiry（既有 ``job_consumer.claim_aiqe_jobs``）；
- ``lease_token`` / ``fencing_token`` 每次重新认领递增，旧 Worker 结果因 token 过期被拒绝；
- 非幂等步骤不得盲目重试（由调用方决定 requeue 还是 BLOCKED）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun


class StaleLeaseError(PermissionError):
    """持有过期租约的 Worker 尝试写入结果。"""

    code = "STALE_LEASE"

    def __init__(self, *, node_run_id: str, fencing_token: int, current_token: int) -> None:
        super().__init__(
            f"STALE_LEASE: node {node_run_id} token={fencing_token} < current={current_token}"
        )
        self.node_run_id = node_run_id
        self.fencing_token = fencing_token
        self.current_token = current_token


class LeaseExpired(PermissionError):
    code = "LEASE_EXPIRED"

    def __init__(self, *, job_id: int | str, expires_at: datetime | None) -> None:
        super().__init__(f"LEASE_EXPIRED: job {job_id} expires_at={expires_at}")
        self.job_id = job_id
        self.expires_at = expires_at


@dataclass(frozen=True)
class LeaseContext:
    job_id: int
    attempt: int
    node_run_id: str
    expires_at: datetime | None = None

    @property
    def fencing_token(self) -> int:
        return int(self.attempt)


def _aware(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def get_node(db: Session, node_run_id: str) -> NodeRun | None:
    return db.scalar(select(NodeRun).where(NodeRun.id == str(node_run_id)))


def bump_fencing_token(db: Session, node_run_id: str, *, token: int) -> int:
    """认领时把节点 token 提升到不小于给定值；返回最终 token。"""
    node = get_node(db, node_run_id)
    if node is None:
        raise LookupError(node_run_id)
    current = int(node.fencing_token or 0)
    node.fencing_token = max(current, int(token))
    db.flush()
    return int(node.fencing_token)


def assert_current(
    db: Session,
    *,
    node_run_id: str,
    fencing_token: int | None,
    now: datetime | None = None,
    job_expires_at: datetime | None = None,
    job_id: int | str = "",
) -> NodeRun:
    """校验 fencing token 与租约有效期；不通过即拒绝写入。"""
    node = get_node(db, node_run_id)
    if node is None:
        raise LookupError(node_run_id)
    if fencing_token is not None:
        current = int(node.fencing_token or 0)
        if int(fencing_token) < current:
            raise StaleLeaseError(
                node_run_id=node.id, fencing_token=int(fencing_token), current_token=current
            )
    expires = _aware(job_expires_at)
    if expires is not None and expires <= (now or datetime.now(UTC)):
        raise LeaseExpired(job_id=job_id, expires_at=expires)
    return node


def assert_writable(
    db: Session, *, node_run_id: str, fencing_token: int | None
) -> NodeRun:
    """仅校验 token（终态回写不要求 lease 未过期，由 Reconciler 负责兜底）。"""
    return assert_current(db, node_run_id=node_run_id, fencing_token=fencing_token)


__all__ = [
    "LeaseContext",
    "LeaseExpired",
    "StaleLeaseError",
    "assert_current",
    "assert_writable",
    "bump_fencing_token",
    "get_node",
]
