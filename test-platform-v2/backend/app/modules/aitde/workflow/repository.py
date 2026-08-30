"""AITDE V3.4 repository (V34).

CRUD for the Durable Runtime tables. All queries honour the tenant boundary via
``project_id`` where the aggregate has one.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.aitde.workflow.models import (
    ApprovalRequest,
    PolicyProfile,
    RuntimeIdempotencyKey,
    SecretRef,
    WorkerCapability,
    WorkerNode,
    WorkflowRun,
)


# ── WorkerNode / WorkerCapability ────────────────────────────────────────────


def upsert_worker_heartbeat(
    db: Session, worker_key: str, data: dict[str, Any]
) -> WorkerNode:
    """Register or refresh a worker heartbeat (V34-003 idempotent registration)."""
    row = db.scalar(select(WorkerNode).where(WorkerNode.worker_key == worker_key))
    if row is None:
        row = WorkerNode(worker_key=worker_key, **data)
        db.add(row)
    else:
        row.network_zone = data.get("network_zone", row.network_zone)
        row.version = data.get("version", row.version)
        row.machine_identity = data.get("machine_identity", row.machine_identity)
        row.tags_json = data.get("tags_json", row.tags_json)
        row.last_heartbeat_at = data.get("last_heartbeat_at", row.last_heartbeat_at)
        row.status = data.get("status", row.status)
    db.commit()
    db.refresh(row)
    return row


def list_workers(db: Session, project_id: int | None = None) -> list[WorkerNode]:
    stmt = select(WorkerNode).order_by(WorkerNode.id.desc())
    if project_id is not None:
        # Worker nodes are global by design; keep the signature compatible.
        stmt = stmt
    return list(db.scalars(stmt).all())


def get_worker(db: Session, worker_id: int) -> WorkerNode | None:
    return db.scalar(select(WorkerNode).where(WorkerNode.id == worker_id))


def list_worker_capabilities(db: Session, worker_id: int) -> list[WorkerCapability]:
    return list(
        db.scalars(
            select(WorkerCapability)
            .where(WorkerCapability.worker_id == worker_id)
            .order_by(WorkerCapability.capability.asc())
        ).all()
    )


def set_worker_status(db: Session, worker_id: int, status: str) -> WorkerNode | None:
    row = get_worker(db, worker_id)
    if row is None:
        return None
    row.status = status
    db.commit()
    db.refresh(row)
    return row


# ── WorkflowRun ──────────────────────────────────────────────────────────────


def create_workflow_run(db: Session, data: dict[str, Any]) -> WorkflowRun:
    row = WorkflowRun(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_workflow_run(db: Session, workflow_run_id: int, project_id: int) -> WorkflowRun | None:
    return db.scalar(
        select(WorkflowRun).where(
            WorkflowRun.id == workflow_run_id, WorkflowRun.project_id == project_id
        )
    )


def get_workflow_run_by_temporal_id(
    db: Session, temporal_workflow_id: str
) -> WorkflowRun | None:
    return db.scalar(
        select(WorkflowRun).where(WorkflowRun.temporal_workflow_id == temporal_workflow_id)
    )


def list_workflow_runs(
    db: Session, project_id: int, page: int = 1, page_size: int = 20
) -> tuple[list[WorkflowRun], int]:
    count_stmt = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.project_id == project_id
    )
    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.project_id == project_id)
        .order_by(WorkflowRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def update_workflow_run(
    db: Session, row: WorkflowRun, data: dict[str, Any]
) -> WorkflowRun:
    for field, value in data.items():
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


# ── Idempotency ──────────────────────────────────────────────────────────────


def acquire_idempotency_key(
    db: Session, scope: str, key_hash: str, resource_type: str
) -> tuple[RuntimeIdempotencyKey | None, bool]:
    """Create the key or return the existing one (idempotent under UNIQUE).

    Returns ``(row, created)`` where ``created`` is True only when this call
    actually inserted it (i.e. it is the first delivery of the side effect).
    """
    existing = db.scalar(
        select(RuntimeIdempotencyKey).where(
            RuntimeIdempotencyKey.scope == scope,
            RuntimeIdempotencyKey.key_hash == key_hash,
        )
    )
    if existing is not None:
        return existing, False
    row = RuntimeIdempotencyKey(
        scope=scope, key_hash=key_hash, resource_type=resource_type
    )
    db.add(row)
    try:
        db.commit()
    except Exception:  # noqa: BLE001 — concurrent insert lost the race
        db.rollback()
        winner = db.scalar(
            select(RuntimeIdempotencyKey).where(
                RuntimeIdempotencyKey.scope == scope,
                RuntimeIdempotencyKey.key_hash == key_hash,
            )
        )
        return winner, False
    db.refresh(row)
    return row, True


# ── Policy / SecretRef / Approval ────────────────────────────────────────────


def create_policy_profile(db: Session, data: dict[str, Any]) -> PolicyProfile:
    row = PolicyProfile(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_policy_profiles(db: Session, project_id: int) -> list[PolicyProfile]:
    return list(
        db.scalars(
            select(PolicyProfile)
            .where(PolicyProfile.project_id == project_id)
            .order_by(PolicyProfile.id.desc())
        ).all()
    )


def create_secret_ref(db: Session, data: dict[str, Any]) -> SecretRef:
    row = SecretRef(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_secret_refs(db: Session, project_id: int) -> list[SecretRef]:
    return list(
        db.scalars(
            select(SecretRef)
            .where(SecretRef.project_id == project_id)
            .order_by(SecretRef.id.desc())
        ).all()
    )


def create_approval(db: Session, data: dict[str, Any]) -> ApprovalRequest:
    row = ApprovalRequest(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_approvals(db: Session, project_id: int) -> list[ApprovalRequest]:
    return list(
        db.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.project_id == project_id)
            .order_by(ApprovalRequest.id.desc())
        ).all()
    )


def get_approval(db: Session, approval_id: int, project_id: int) -> ApprovalRequest | None:
    return db.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id, ApprovalRequest.project_id == project_id
        )
    )


def resolve_approval(
    db: Session, row: ApprovalRequest, status: str, approved_by: int
) -> ApprovalRequest:
    from datetime import datetime

    row.status = status
    row.approved_by = approved_by
    row.resolved_at = datetime.now()
    db.commit()
    db.refresh(row)
    return row
