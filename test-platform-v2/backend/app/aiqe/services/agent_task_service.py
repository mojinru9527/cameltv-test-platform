"""V16-013：A0 AgentTask 状态机（Draft → 审批 → 真实 run_plan 执行）。

- DRAFT 不执行任何 Agent；
- APPROVED 前调用 run 一律拒绝；
- run 通过 orchestrator.run_plan 持久化每个 Agent 的 AgentExecution；
- 每个任务必须有执行记录；任一必需 Agent 失败 → Task 不得 COMPLETED；
- 取消/重复请求/终态重跑有明确规则。
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.agents.orchestrator import (
    AgentPlan,
    AgentTask as PlanTask,
    build_plan,
    run_plan,
)
from app.aiqe.models.agent import AgentExecution, AgentTask
from app.aiqe.services.evidence_resolver import (
    EvidenceResolverError,
    build_evidence_resolver,
)

STATUSES = (
    "DRAFT",
    "PENDING_APPROVAL",
    "APPROVED",
    "QUEUED",
    "RUNNING",
    "WAITING_HUMAN",
    "COMPLETED",
    "FAILED",
    "BLOCKED",
    "CANCELLED",
)
TERMINAL = frozenset({"COMPLETED", "FAILED", "BLOCKED", "CANCELLED"})
_ALLOWED: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"PENDING_APPROVAL", "APPROVED", "CANCELLED"}),
    "PENDING_APPROVAL": frozenset({"APPROVED", "CANCELLED"}),
    "APPROVED": frozenset({"QUEUED", "CANCELLED"}),
    "QUEUED": frozenset({"RUNNING", "CANCELLED", "BLOCKED"}),
    "RUNNING": frozenset({"COMPLETED", "FAILED", "BLOCKED", "WAITING_HUMAN", "CANCELLED"}),
    "WAITING_HUMAN": frozenset({"RUNNING", "CANCELLED", "BLOCKED"}),
}


class AgentTaskError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _transition(task: AgentTask, target: str) -> None:
    current = str(task.status)
    if target not in _ALLOWED.get(current, frozenset()):
        raise AgentTaskError("INVALID_TRANSITION", f"{current} -> {target}")
    task.status = target
    task.updated_at = datetime.now(UTC)


def plan_to_dict(plan: AgentPlan) -> dict[str, Any]:
    return {
        "plan_id": plan.plan_id,
        "goal": plan.goal,
        "tasks": [
            {
                "task_id": task.task_id,
                "agent_key": task.agent_key,
                "depends_on": list(task.depends_on),
                "max_attempts": task.max_attempts,
                "timeout_seconds": task.timeout_seconds,
                "allowed_tools": list(task.allowed_tools),
                "input_refs": list(task.input_refs),
                "request": task.request,
            }
            for task in plan.tasks
        ],
    }


def plan_from_dict(payload: Mapping[str, Any]) -> AgentPlan:
    tasks = tuple(
        PlanTask(
            task_id=str(item["task_id"]),
            agent_key=str(item["agent_key"]),
            depends_on=tuple(str(dep) for dep in item.get("depends_on") or []),
            max_attempts=int(item.get("max_attempts") or 1),
            timeout_seconds=int(item.get("timeout_seconds") or 300),
            allowed_tools=tuple(str(tool) for tool in item.get("allowed_tools") or []),
            input_refs=tuple(str(ref) for ref in item.get("input_refs") or []),
            request=str(item.get("request") or ""),
        )
        for item in payload.get("tasks") or []
    )
    return AgentPlan(
        plan_id=str(payload.get("plan_id") or ""),
        goal=str(payload.get("goal") or ""),
        tasks=tasks,
    )


def get_task(db: Session, task_id: str, *, project_id: int) -> AgentTask:
    row = db.get(AgentTask, str(task_id))
    if row is None or int(row.project_id or 0) != int(project_id):
        raise AgentTaskError("TASK_NOT_FOUND", f"AgentTask 不存在: {task_id}")
    return row


def create_task(
    db: Session,
    *,
    project_id: int,
    goal: str,
    include: tuple[str, ...] | None = None,
    input_refs: list[str] | None = None,
    requested_by: int | None = None,
    idempotency_key: str | None = None,
    run_id: str | None = None,
    task_type: str = "A0_PLAN",
) -> AgentTask:
    if idempotency_key:
        existing = db.scalar(
            select(AgentTask).where(
                AgentTask.project_id == int(project_id),
                AgentTask.idempotency_key == str(idempotency_key),
            )
        )
        if existing is not None:
            return existing
    plan = build_plan(goal, include=include)
    payload = plan_to_dict(plan)
    row = AgentTask(
        project_id=int(project_id),
        task_type=str(task_type),
        status="DRAFT",
        goal=str(goal),
        input_refs_json=list(input_refs or []),
        plan_json=payload,
        plan_hash=_hash(payload),
        agent_registry_version="v16.1",
        prompt_version=_hash(plan.goal)[:24],
        toolset_version="v16.1",
        requested_by=requested_by,
        run_id=str(run_id) if run_id else None,
        idempotency_key=str(idempotency_key) if idempotency_key else None,
    )
    db.add(row)
    db.flush()
    return row


def submit_task(db: Session, task_id: str, *, project_id: int) -> AgentTask:
    row = get_task(db, task_id, project_id=project_id)
    if row.status == "PENDING_APPROVAL":
        return row
    _transition(row, "PENDING_APPROVAL")
    db.flush()
    return row


def approve_task(
    db: Session,
    task_id: str,
    *,
    project_id: int,
    approved_by: int | None,
    reason: str = "",
    expected_plan_hash: str | None = None,
) -> AgentTask:
    row = get_task(db, task_id, project_id=project_id)
    if approved_by is None:
        raise AgentTaskError("APPROVER_REQUIRED", "审批必须提供 approved_by")
    if expected_plan_hash and expected_plan_hash != row.plan_hash:
        raise AgentTaskError("PLAN_CHANGED", "计划 hash 与审批请求不一致")
    if row.status not in {"DRAFT", "PENDING_APPROVAL"}:
        raise AgentTaskError("INVALID_STATUS", f"当前状态不能审批: {row.status}")
    if row.status == "DRAFT":
        _transition(row, "PENDING_APPROVAL")
    # 证据 refs 必须在审批时可由服务端解析（存在/同项目/同 Run）。
    if row.run_id and row.input_refs_json:
        try:
            resolver = build_evidence_resolver(
                db, project_id=int(project_id), run_id=row.run_id
            )
        except EvidenceResolverError as exc:
            raise AgentTaskError("EVIDENCE_UNAVAILABLE", str(exc)) from exc
        for entry in resolver(list(row.input_refs_json)):
            if not entry.get("valid"):
                raise AgentTaskError(
                    "INVALID_EVIDENCE", f"{entry.get('ref')}: {entry.get('reason')}"
                )
    _transition(row, "APPROVED")
    row.approved_by = int(approved_by)
    row.approved_at = datetime.now(UTC)
    row.approval_reason = str(reason or "")[:500]
    db.flush()
    return row


def cancel_task(
    db: Session, task_id: str, *, project_id: int, reason: str = ""
) -> AgentTask:
    row = get_task(db, task_id, project_id=project_id)
    if row.status in TERMINAL:
        raise AgentTaskError("ALREADY_TERMINAL", f"Task 已终态: {row.status}")
    _transition(row, "CANCELLED")
    row.error_code = "CANCELLED"
    row.error_text = str(reason or "")[:2000]
    row.finished_at = datetime.now(UTC)
    db.flush()
    return row


def run_task(
    db: Session,
    task_id: str,
    *,
    project_id: int,
    actor_id: int | None = None,
    llm: Callable[[str, str], str] | None = None,
    executor: Callable[..., Any] | None = None,
    tools: Any = None,
    inputs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """审批后真实执行 plan；每个 Agent 产生 AgentExecution 记录。"""
    row = get_task(db, task_id, project_id=project_id)
    if row.status == "COMPLETED":
        return _result_payload(db, row)
    if row.status in TERMINAL:
        raise AgentTaskError("ALREADY_TERMINAL", f"Task 已终态: {row.status}")
    if row.status not in {"APPROVED", "QUEUED", "WAITING_HUMAN"}:
        raise AgentTaskError(
            "APPROVAL_REQUIRED", f"Task 未审批，禁止执行（当前 {row.status}）"
        )
    plan = plan_from_dict(row.plan_json or {})
    resolver = None
    if row.run_id:
        try:
            resolver = build_evidence_resolver(
                db, project_id=int(project_id), run_id=row.run_id
            )
        except EvidenceResolverError:
            resolver = None
    if tools is None:
        # V16-019：绑定真实实现的 ToolRegistry（生产默认只读，写工具需审批）。
        from app.aiqe.services.tool_registry import build_bound_registry

        tools = build_bound_registry(
            db,
            project_id=int(project_id),
            actor_id=actor_id,
            task_id=row.id,
            approval_token=row.id,
        )
    if row.status == "WAITING_HUMAN":
        _transition(row, "RUNNING")
    elif row.status == "QUEUED":
        _transition(row, "RUNNING")
    else:
        _transition(row, "QUEUED")
        _transition(row, "RUNNING")
    row.started_at = row.started_at or datetime.now(UTC)
    db.flush()
    try:
        result = run_plan(
            db,
            plan,
            project_id=int(project_id),
            actor_id=actor_id,
            llm=llm,
            inputs=inputs,
            tools=tools,
            executor=executor,
            evidence_resolver=resolver,
            idempotency_prefix=f"agent-task:{row.id}",
            run_id=row.run_id,
            parent_task_id=row.id,
        )
    except Exception as exc:
        row.status = "FAILED"
        row.error_code = "EXECUTION_ERROR"
        row.error_text = f"{type(exc).__name__}: {exc}"[:2000]
        row.finished_at = datetime.now(UTC)
        db.flush()
        return _result_payload(db, row)

    executions = list(
        db.scalars(
            select(AgentExecution)
            .where(AgentExecution.parent_task_id == row.id)
            .order_by(AgentExecution.created_at)
        )
    )
    row.result_refs_json = [execution.id for execution in executions]
    statuses = {key: value.get("status") for key, value in result.tasks.items()}
    if any(status == "FAILED" for status in statuses.values()):
        row.status = "FAILED"
        row.error_code = "AGENT_FAILED"
    elif statuses and all(status == "COMPLETED" for status in statuses.values()):
        row.status = "COMPLETED"
    elif any(status == "WAITING_HUMAN" for status in statuses.values()):
        row.status = "WAITING_HUMAN"
    else:
        row.status = "BLOCKED"
        row.error_code = "AGENT_NOT_COMPLETED"
    row.error_text = " | ".join(result.errors)[:2000]
    if row.status in {"COMPLETED", "FAILED", "BLOCKED"}:
        row.finished_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    db.flush()
    return _result_payload(db, row)


def _result_payload(db: Session, row: AgentTask) -> dict[str, Any]:
    executions = list(
        db.scalars(
            select(AgentExecution)
            .where(AgentExecution.parent_task_id == row.id)
            .order_by(AgentExecution.created_at)
        )
    )
    return {
        "task": {
            "id": row.id,
            "project_id": row.project_id,
            "status": row.status,
            "plan_hash": row.plan_hash,
            "approved_by": row.approved_by,
            "approved_at": row.approved_at,
            "error_code": row.error_code,
            "error_text": row.error_text,
            "result_refs": list(row.result_refs_json or []),
        },
        "executions": [
            {
                "id": execution.id,
                "agent_key": execution.agent_key,
                "status": execution.status,
                "task_id": execution.task_id,
                "output_hash": execution.output_hash,
                "needs_human": execution.needs_human,
                "error_text": execution.error_text,
            }
            for execution in executions
        ],
    }


def enqueue_task_job(db: Session, task: AgentTask) -> Any:
    """V16-006/013：审批后通过统一 ExecutionJob + Outbox 排队，不在 HTTP 线程执行。"""
    import json as _json

    from app.aiqe.services import outbox_service
    from app.models.execution_job import ExecutionJob

    job = ExecutionJob(
        project_id=int(task.project_id),
        kind="agent_task",
        status="pending",
        payload_json=_json.dumps({"task_id": task.id, "project_id": task.project_id}),
        case_refs_json=_json.dumps([task.id]),
        env_ref="",
        idempotency_key=f"agent-task:{task.id}",
        execution_kind="AGENT_TASK",
    )
    db.add(job)
    db.flush()
    task.status = "QUEUED"
    task.updated_at = datetime.now(UTC)
    outbox_service.enqueue(
        db,
        project_id=int(task.project_id),
        run_id=task.run_id,
        event_type="agent_task.queued",
        payload={"task_id": task.id, "job_id": job.id},
        producer_event_id=f"agent-task-queued:{task.id}",
    )
    db.flush()
    return job


def execute_task_job(db: Session, job_id: int, **kwargs: Any) -> dict[str, Any]:
    """Worker 入口：消费 agent_task Job 并执行 run_task。"""
    from app.models.execution_job import ExecutionJob

    job = db.get(ExecutionJob, int(job_id))
    if job is None:
        raise AgentTaskError("JOB_NOT_FOUND", f"Job 不存在: {job_id}")
    payload = json.loads(job.payload_json or "{}")
    task_id = str(payload.get("task_id") or "")
    job.status = "running"
    job.started_at = datetime.now(UTC)
    db.flush()
    try:
        result = run_task(
            db,
            task_id,
            project_id=int(payload.get("project_id") or job.project_id or 0),
            **kwargs,
        )
    except Exception as exc:
        job.status = "failed"
        job.error_message = f"{type(exc).__name__}: {exc}"[:2000]
        job.finished_at = datetime.now(UTC)
        db.flush()
        raise
    job.status = "success" if result["task"]["status"] == "COMPLETED" else "failed"
    job.result_json = json.dumps(result, ensure_ascii=False, default=str)[:20000]
    job.finished_at = datetime.now(UTC)
    db.flush()
    return result


__all__ = [
    "STATUSES",
    "TERMINAL",
    "AgentTaskError",
    "approve_task",
    "cancel_task",
    "create_task",
    "enqueue_task_job",
    "execute_task_job",
    "get_task",
    "plan_from_dict",
    "plan_to_dict",
    "run_task",
    "submit_task",
]
