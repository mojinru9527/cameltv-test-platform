"""AITDE V3.4 orchestration service (V34).

High-level operations for the Durable Runtime API: worker registration,
workflow start + status, run resume/retry, policy evaluation, secret-ref
metadata, and approval resolution. Pure-service layer; the Temporal client is
reached only through the gateway.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    ApprovalStatus,
    WorkflowStatus,
    WorkflowType,
    WorkerStatus,
)
from app.modules.aitde.workflow import repository
from app.modules.aitde.workflow.gateway import temporal_gateway
from app.modules.aitde.workflow.policy import policy_gateway
from app.modules.aitde.workflow.schemas import (
    PolicyDecisionIn,
    PolicyProfileIn,
    SecretRefIn,
    WorkerHeartbeatIn,
)


# ── Worker ───────────────────────────────────────────────────────────────────


def register_worker(db: Session, data: WorkerHeartbeatIn) -> dict[str, Any]:
    """Register / heartbeat a worker and upsert its capabilities."""
    row = repository.upsert_worker_heartbeat(
        db,
        data.worker_key,
        {
            "name": data.name,
            "network_zone": data.network_zone.value,
            "status": WorkerStatus.ONLINE.value,
            "version": data.version,
            "machine_identity": data.machine_identity,
            "tags_json": json.dumps(data.tags),
            "last_heartbeat_at": datetime.now(),
        },
    )
    # Replace capabilities for the worker to reflect the current set.
    caps = repository.list_worker_capabilities(db, row.id)
    for cap in caps:
        if cap.capability not in {c.value for c in data.capabilities}:
            db.delete(cap)
    for cap in data.capabilities:
        existing = next(
            (c for c in caps if c.capability == cap.value), None
        )
        if existing is None:
            db.add(
                repository.WorkerCapability(
                    worker_id=row.id, capability=cap.value, version=data.version
                )
            )
    db.commit()
    db.refresh(row)
    return worker_to_dict(row)


def list_workers(db: Session) -> list[dict[str, Any]]:
    items = repository.list_workers(db)
    return [worker_to_dict(w) for w in items]


def get_worker(db: Session, worker_id: int) -> dict[str, Any]:
    row = repository.get_worker(db, worker_id)
    if row is None:
        raise APIException(code=404, msg="Worker 不存在", http_status=404)
    data = worker_to_dict(row)
    data["capabilities"] = [
        c.capability for c in repository.list_worker_capabilities(db, worker_id)
    ]
    return data


def set_worker_status(db: Session, worker_id: int, status: str) -> dict[str, Any]:
    row = repository.set_worker_status(db, worker_id, status)
    if row is None:
        raise APIException(code=404, msg="Worker 不存在", http_status=404)
    return worker_to_dict(row)


def worker_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "worker_key": row.worker_key,
        "name": row.name,
        "network_zone": row.network_zone,
        "status": row.status,
        "version": row.version,
        "machine_identity": row.machine_identity,
        "tags_json": row.tags_json,
        "last_heartbeat_at": row.last_heartbeat_at,
        "registered_at": row.registered_at,
    }


# ── Workflow run ─────────────────────────────────────────────────────────────


def start_scenario_execution(
    db: Session,
    project_id: int,
    workflow_id: str,
    scenario_input: dict[str, Any],
    run_id: int | None = None,
    mission_id: int | None = None,
    network_zone: str | None = None,
    required_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Persist a WorkflowRun row (idempotent by temporal_workflow_id) and start it.

    When ``network_zone`` + ``required_capabilities`` are supplied, the run is
    routed to a TaskQueue by the Capability Router (V34-006); otherwise the
    configured default queue is used.
    """
    existing = repository.get_workflow_run_by_temporal_id(db, workflow_id)
    if existing is not None:
        return workflow_run_to_dict(existing)

    task_queue = None
    if network_zone is not None:
        from app.modules.aitde.workflow.router import task_queue_router

        task_queue = task_queue_router.select_queue(
            db,
            network_zone=network_zone,
            required_capabilities=required_capabilities or [],
        )

    async def _start() -> dict[str, Any]:
        return await temporal_gateway.start_scenario_execution(
            workflow_id, run_id, scenario_input, task_queue=task_queue
        )

    import asyncio

    gateway_result = asyncio.run(_start())
    # Record after successful Temporal start (keeps the row truthful).
    row = repository.create_workflow_run(
        db,
        {
            "project_id": project_id,
            "mission_id": mission_id,
            "run_id": run_id,
            "workflow_type": WorkflowType.SCENARIO_EXECUTION.value,
            "temporal_namespace": settings.temporal_namespace,
            "temporal_workflow_id": workflow_id,
            "temporal_run_id": gateway_result.get("temporal_run_id"),
            "status": WorkflowStatus.FINISHED.value,
            "started_at": datetime.now(),
            "closed_at": datetime.now(),
        },
    )
    return workflow_run_to_dict(row)


def get_workflow_run(db: Session, workflow_run_id: int, project_id: int) -> dict[str, Any]:
    row = repository.get_workflow_run(db, workflow_run_id, project_id)
    if row is None:
        raise APIException(code=404, msg="WorkflowRun 不存在", http_status=404)
    return workflow_run_to_dict(row)


def list_workflow_runs(
    db: Session, project_id: int, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    items, total = repository.list_workflow_runs(db, project_id, page, page_size)
    return [workflow_run_to_dict(r) for r in items], total


def resume_run(db: Session, project_id: int, workflow_id: str, signal: str) -> dict[str, Any]:
    """Signal a WAITING_APPROVAL / WAITING_WORKER / FAILED workflow to resume."""
    async def _resume() -> None:
        await temporal_gateway.signal_workflow(workflow_id, signal, {"resume": True})

    import asyncio

    asyncio.run(_resume())
    row = repository.get_workflow_run_by_temporal_id(db, workflow_id)
    if row is not None:
        return workflow_run_to_dict(
            repository.update_workflow_run(
                db, row, {"status": WorkflowStatus.RESUMING.value}
            )
        )
    return {"workflow_id": workflow_id, "status": WorkflowStatus.RESUMING.value}


def workflow_run_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "run_id": row.run_id,
        "workflow_type": row.workflow_type,
        "temporal_namespace": row.temporal_namespace,
        "temporal_workflow_id": row.temporal_workflow_id,
        "temporal_run_id": row.temporal_run_id,
        "status": row.status,
        "started_at": row.started_at,
        "closed_at": row.closed_at,
        "created_at": row.created_at,
    }


# ── Policy / Secret / Approval ───────────────────────────────────────────────


def evaluate_policy(db: Session, request: PolicyDecisionIn) -> dict[str, Any]:
    decision, reason = policy_gateway.evaluate(db, request)
    return {"decision": decision, "reason": reason}


def create_policy_profile(db: Session, data: PolicyProfileIn) -> dict[str, Any]:
    row = repository.create_policy_profile(
        db,
        {
            "project_id": data.project_id,
            "name": data.name,
            "policy_type": data.policy_type.value,
            "version": data.version,
            "document_json": json.dumps(data.document),
            "status": "ACTIVE",
        },
    )
    return {
        "id": row.id,
        "project_id": row.project_id,
        "name": row.name,
        "policy_type": row.policy_type,
        "version": row.version,
        "document_json": row.document_json,
        "status": row.status,
        "created_at": row.created_at,
    }


def list_policy_profiles(db: Session, project_id: int) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "name": r.name,
            "policy_type": r.policy_type,
            "version": r.version,
            "document_json": r.document_json,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in repository.list_policy_profiles(db, project_id)
    ]


def create_secret_ref(db: Session, data: SecretRefIn) -> dict[str, Any]:
    # V34-008 invariant: the API never receives or returns a secret value — only
    # the metadata that lets the worker resolver fetch it at runtime. Reject any
    # scope key that could carry a secret value (defense-in-depth allowlist).
    _REJECT_SCOPE_KEYS = {"value", "secret", "token", "password", "passwd", "api_key", "apikey", "key", "credential"}
    lower_scope = {str(k).lower() for k in (data.scope or {})}
    if lower_scope & _REJECT_SCOPE_KEYS:
        raise APIException(code=400, msg="Secret value 禁止进入 Control Plane", http_status=400)
    row = repository.create_secret_ref(
        db,
        {
            "project_id": data.project_id,
            "name": data.name,
            "provider": data.provider,
            "external_ref": data.external_ref,
            "purpose": data.purpose,
            "scope_json": json.dumps(data.scope),
            "status": "ACTIVE",
        },
    )
    return {
        "id": row.id,
        "project_id": row.project_id,
        "name": row.name,
        "provider": row.provider,
        "external_ref": row.external_ref,
        "purpose": row.purpose,
        "scope_json": row.scope_json,
        "status": row.status,
        "created_at": row.created_at,
    }


def list_secret_refs(db: Session, project_id: int) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "name": r.name,
            "provider": r.provider,
            "external_ref": r.external_ref,
            "purpose": r.purpose,
            "scope_json": r.scope_json,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in repository.list_secret_refs(db, project_id)
    ]


def list_approvals(db: Session, project_id: int) -> list[dict[str, Any]]:
    return [
        approval_to_dict(r) for r in repository.list_approvals(db, project_id)
    ]


def resolve_approval(
    db: Session, approval_id: int, project_id: int, approved: bool, approved_by: int
) -> dict[str, Any]:
    row = repository.get_approval(db, approval_id, project_id)
    if row is None:
        raise APIException(code=404, msg="Approval 不存在", http_status=404)
    status = ApprovalStatus.APPROVED.value if approved else ApprovalStatus.REJECTED.value
    updated = repository.resolve_approval(db, row, status, approved_by)

    # V34-011: signal the waiting workflow so it resumes or aborts the dangerous
    # step. The temporal_workflow_id is carried in request_json (set at creation);
    # resolve by run_id lookup as a fallback.
    temporal_workflow_id = _extract_temporal_workflow_id(row)
    if temporal_workflow_id:
        _signal_approval(temporal_workflow_id, {"approved": approved, "reason": status})

    return approval_to_dict(updated)


def _extract_temporal_workflow_id(row: Any) -> str | None:
    try:
        import json as _json

        req = _json.loads(row.request_json or "{}")
        if isinstance(req, dict) and req.get("temporal_workflow_id"):
            return str(req["temporal_workflow_id"])
    except (ValueError, TypeError):
        pass
    if row.run_id:
        wf = repository.get_workflow_run_by_run_id(row.run_id)
        if wf is not None:
            return wf.temporal_workflow_id
    return None


def _signal_approval(temporal_workflow_id: str, payload: dict[str, Any]) -> None:
    import asyncio

    async def _signal() -> None:
        await temporal_gateway.signal_workflow(temporal_workflow_id, "approve", payload)

    try:
        asyncio.run(_signal())
    except Exception as exc:  # noqa: BLE001 — approval persistence already done
        logger.warning("[temporal] approval signal failed: %s", exc)


def approval_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "run_id": row.run_id,
        "action_type": row.action_type,
        "request_json": row.request_json,
        "policy_decision": row.policy_decision,
        "status": row.status,
        "requested_by": row.requested_by,
        "approved_by": row.approved_by,
        "created_at": row.created_at,
        "resolved_at": row.resolved_at,
    }
