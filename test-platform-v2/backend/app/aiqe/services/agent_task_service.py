"""V16-013：A0 AgentTask 状态机（Draft → 审批 → 真实 run_plan 执行）。

- DRAFT 不执行任何 Agent；
- APPROVED 前调用 run 一律拒绝（`approved_by` + `approved_at` 必须存在）；
- run 通过 orchestrator.run_plan 持久化每个 Agent 的 AgentExecution；
- 每个任务必须有执行记录；任一必需 Agent 失败 → Task 不得 COMPLETED；
- 取消/重复请求/终态重跑有明确规则。

V1.6.2（FIX-005）加固：
- 可选 ``base_sha`` / ``head_sha`` / ``repo`` 变更范围注入任务上下文，A5 通过
  ``read_git_diff`` 读取服务端真实 diff；
- A5 缺少真实 SHA、或没有 ALLOW 的 ``read_git_diff`` 审计时，任务必须 BLOCKED
  （``error_code=A5_NOT_PROVEN``），不得输出“无影响 PASS”；
- Worker 执行路径（``execute_task_job``）不再要求测试注入 LLM：经
  :func:`resolve_project_llm` 解析项目级 Provider；未配置 → None，Agent fail-closed。
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import replace
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
from app.aiqe.models.tool import ToolExecutionAudit
from app.aiqe.services.evidence_resolver import (
    EvidenceResolverError,
    build_evidence_resolver,
)

#: 变更范围参数名（存入 ``plan_json["params"]``，不新增 DB 迁移）。
CHANGE_SCOPE_KEY = "params"
#: A5 证据不足的阻断码（任务不得 COMPLETED）。
A5_NOT_PROVEN = "A5_NOT_PROVEN"
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_REPO_MAX_CHARS = 200

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


def normalize_change_scope(
    *,
    base_sha: str | None = None,
    head_sha: str | None = None,
    repo: str | None = None,
) -> dict[str, str]:
    """校验并规范化变更范围（A5 的 base/head SHA）。

    规则（fail-closed）：
    - 两个 SHA 必须同时提供，否则 ``SHA_INCOMPLETE``；
    - 必须是完整 40 位小写 hex（``read_git_diff`` 的服务端契约），否则 ``SHA_INVALID``；
    - base == head 表示空 diff，无分析价值，直接拒绝；
    - ``repo`` 只作为展示/追踪标签，不参与服务端仓库路径解析。
    """
    base = str(base_sha or "").strip().lower()
    head = str(head_sha or "").strip().lower()
    name = str(repo or "").strip()
    if not base and not head:
        return {}
    if not base or not head:
        raise AgentTaskError(
            "SHA_INCOMPLETE", "base_sha 与 head_sha 必须同时提供（单边 SHA 不能做变更影响）"
        )
    for key, value in (("base_sha", base), ("head_sha", head)):
        if not _SHA_PATTERN.match(value):
            raise AgentTaskError(
                "SHA_INVALID", f"{key} 必须是完整 40 位小写 hex SHA，收到: {value!r}"
            )
    if base == head:
        raise AgentTaskError("SHA_INVALID", "base_sha 与 head_sha 相同，diff 为空")
    scope = {"base_sha": base, "head_sha": head}
    if name:
        scope["repo"] = name[:_REPO_MAX_CHARS]
    return scope


def task_change_scope(task: AgentTask) -> dict[str, str]:
    """从持久化 plan 读取变更范围（读取时重新校验，防止被篡改的 SHA 进入工具层）。"""
    params = (task.plan_json or {}).get(CHANGE_SCOPE_KEY) or {}
    if not isinstance(params, Mapping):
        return {}
    try:
        return normalize_change_scope(
            base_sha=params.get("base_sha"),
            head_sha=params.get("head_sha"),
            repo=params.get("repo"),
        )
    except AgentTaskError:
        return {}


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
    base_sha: str | None = None,
    head_sha: str | None = None,
    repo: str | None = None,
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
    scope = normalize_change_scope(base_sha=base_sha, head_sha=head_sha, repo=repo)
    plan = build_plan(goal, include=include)
    payload = plan_to_dict(plan)
    # plan_hash 只覆盖计划本身（审批锁定的是 Agent/Tool 编排）；
    # 变更范围是执行上下文，单独存 params，并在读取时重新校验。
    plan_hash = _hash(payload)
    if scope:
        payload[CHANGE_SCOPE_KEY] = dict(scope)
    row = AgentTask(
        project_id=int(project_id),
        task_type=str(task_type),
        status="DRAFT",
        goal=str(goal),
        input_refs_json=list(input_refs or []),
        plan_json=payload,
        plan_hash=plan_hash,
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
    # FIX-005：审批人/审批时间必须真实落库，状态被外部改写也不能绕过审批。
    if row.approved_by is None or row.approved_at is None:
        raise AgentTaskError(
            "APPROVAL_REQUIRED", "Task 缺少审批人/审批时间，禁止执行"
        )
    plan = plan_from_dict(row.plan_json or {})
    scope = task_change_scope(row)
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
    # FIX-005：worker 路径不再依赖调用方注入模型；按项目 Provider 受控解析。
    if llm is None:
        llm = resolve_project_llm(db, project_id=int(project_id))
    if scope:
        plan = _inject_change_scope(plan, scope)
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
            extra_context=dict(scope) or None,
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
        try:
            from app.aiqe.observability.metrics import metrics

            metrics.inc(
                "aiqe_agent_task_failure_total",
                {"project_id": row.project_id, "reason": "AGENT_FAILED"},
            )
        except Exception:
            pass
    elif statuses and all(status == "COMPLETED" for status in statuses.values()):
        row.status = "COMPLETED"
    elif any(status == "WAITING_HUMAN" for status in statuses.values()):
        row.status = "WAITING_HUMAN"
    else:
        row.status = "BLOCKED"
        row.error_code = "AGENT_NOT_COMPLETED"
    row.error_text = " | ".join(result.errors)[:2000]
    # FIX-005：A5 缺 SHA / 缺 read_git_diff 审计 → 任务必须 BLOCKED，不得 COMPLETED。
    problems = _change_impact_problems(db, row=row, plan=plan, scope=scope)
    if problems:
        _mark_change_impact_not_proven(db, row=row, problems=problems)
    if row.status in {"COMPLETED", "FAILED", "BLOCKED"}:
        row.finished_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    db.flush()
    return _result_payload(db, row)


def _inject_change_scope(plan: AgentPlan, scope: Mapping[str, str]) -> AgentPlan:
    """把 base/head SHA 注入 A5 任务输入（同时进入 AgentContext.extra/references）。

    注入发生在**运行时计划实例**上：``plan_json`` 与 ``plan_hash`` 保持审批时的原样，
    但 ``AgentExecution.input_text`` 会保留真实 SHA，便于审计回查注入事实。
    """
    suffix = "\n[CHANGE_SCOPE] base_sha={base_sha} head_sha={head_sha}".format(
        base_sha=scope.get("base_sha", ""), head_sha=scope.get("head_sha", "")
    )
    if scope.get("repo"):
        suffix += f" repo={scope['repo']}"
    tasks = tuple(
        replace(task, request=f"{task.request}{suffix}") if task.agent_key == "A5" else task
        for task in plan.tasks
    )
    return AgentPlan(plan_id=plan.plan_id, goal=plan.goal, tasks=tasks)


def _a5_executions(db: Session, task_id: str) -> list[AgentExecution]:
    return [
        row
        for row in db.scalars(
            select(AgentExecution)
            .where(AgentExecution.parent_task_id == task_id)
            .order_by(AgentExecution.created_at)
        )
        if str(row.agent_key or "").upper() == "A5"
    ]


def _change_impact_problems(
    db: Session, *, row: AgentTask, plan: AgentPlan, scope: Mapping[str, str]
) -> list[str]:
    """A5 证据完整性校验：缺 SHA / 缺 ALLOW 的 read_git_diff / SHA 不匹配。"""
    if not any(task.agent_key == "A5" for task in plan.tasks):
        return []
    base_sha = str(scope.get("base_sha") or "")
    head_sha = str(scope.get("head_sha") or "")
    problems: list[str] = []
    if not (base_sha and head_sha):
        problems.append(
            "MISSING_CHANGE_SHA: 未提供真实 base_sha/head_sha，A5 不得输出“无影响”结论"
        )
    audits = list(
        db.scalars(
            select(ToolExecutionAudit).where(
                ToolExecutionAudit.task_id == row.id,
                ToolExecutionAudit.tool_name == "read_git_diff",
            )
        )
    )
    allowed = [item for item in audits if str(item.decision) == "ALLOW"]
    if not allowed:
        problems.append(
            "READ_GIT_DIFF_NOT_EXECUTED: ToolExecutionAudit 中没有 ALLOW 的 read_git_diff 调用"
        )
    else:
        mismatched = [
            dict(item.args_summary_json or {})
            for item in allowed
            if str((item.args_summary_json or {}).get("base_sha") or "") != base_sha
            or str((item.args_summary_json or {}).get("head_sha") or "") != head_sha
        ]
        if mismatched:
            problems.append(
                "READ_GIT_DIFF_SHA_MISMATCH: read_git_diff 参数与任务 base/head SHA 不一致"
            )
    return problems


def _mark_change_impact_not_proven(
    db: Session, *, row: AgentTask, problems: list[str]
) -> None:
    """把 A5 执行与任务标记为 NOT_PROVEN（BLOCKED），覆盖已被误判的 COMPLETED。"""
    detail = " | ".join(problems)
    if str(row.status) != "COMPLETED":
        # 任务本来就没有 PASS，仍把 A5 记录标注为不可采信，便于审计回查。
        for execution in _a5_executions(db, row.id):
            if str(execution.status) not in {"COMPLETED", "succeeded"}:
                continue
            _annotate_execution(execution, detail)
        return
    for execution in _a5_executions(db, row.id):
        if str(execution.status) in {"COMPLETED", "succeeded"}:
            _annotate_execution(execution, detail)
    row.status = "BLOCKED"
    row.error_code = A5_NOT_PROVEN
    row.error_text = detail[:2000]
    row.finished_at = datetime.now(UTC)
    try:
        from app.aiqe.observability.metrics import metrics

        metrics.inc(
            "aiqe_agent_task_not_proven_total",
            {"project_id": row.project_id, "reason": A5_NOT_PROVEN},
        )
    except Exception:
        pass


def _annotate_execution(execution: AgentExecution, detail: str) -> None:
    warnings = [str(item) for item in (execution.warnings_json or [])]
    if A5_NOT_PROVEN not in warnings:
        warnings.append(A5_NOT_PROVEN)
    execution.warnings_json = warnings
    execution.status = "BLOCKED"
    execution.needs_human = True
    execution.error_text = f"NOT_PROVEN: {detail}"[:2000]
    execution.finished_at = execution.finished_at or datetime.now(UTC)


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
            "change_scope": task_change_scope(row),
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
    """V16-006/013：审批后通过统一 ExecutionJob + Outbox 排队，不在 HTTP 线程执行。

    FIX-005：入队本身也必须校验审批事实。此前 ``enqueue_task_job`` 直接把任意
    状态写成 QUEUED，可绕过 ``/run`` 的 APPROVED 前置检查。
    """
    import json as _json

    from app.aiqe.services import outbox_service
    from app.models.execution_job import ExecutionJob

    if str(task.status) != "APPROVED" or task.approved_by is None or task.approved_at is None:
        raise AgentTaskError(
            "APPROVAL_REQUIRED",
            f"只有已审批 Task 可以入队（当前 {task.status}，审批人 {task.approved_by}）",
        )
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
    _transition(task, "QUEUED")
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


def resolve_project_llm(
    db: Session, project_id: int
) -> Callable[[str, str], str] | None:
    """Worker 执行 AgentTask 时的**受控模型边界**。

    生产语义：按项目级 AI Provider 配置解析真实模型；未配置返回 ``None``，
    Agent 以 ``MODEL_UNAVAILABLE`` fail-closed，不会静默降级为假成功。

    测试语义：CI 可 monkeypatch 本函数注入 deterministic stub，但必须在用例里
    标注 ``controlled_llm_test``，stub 结果不得当作生产模型质量结论。
    """
    try:
        from app.services import ai_client

        if not ai_client.is_configured(db, int(project_id)):
            return None
    except Exception:  # 配置读取失败按不可用处理（fail-closed）
        return None

    def _llm(system_prompt: str, user_message: str) -> str:
        summary = ai_client.chat_completions_full(
            db,
            int(project_id),
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0,
            json_mode=True,
            cache_namespace="aiqe-agent-task",
        )
        return str(summary.get("content") or "")

    return _llm


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
    "A5_NOT_PROVEN",
    "CHANGE_SCOPE_KEY",
    "STATUSES",
    "TERMINAL",
    "AgentTaskError",
    "approve_task",
    "cancel_task",
    "create_task",
    "enqueue_task_job",
    "execute_task_job",
    "get_task",
    "normalize_change_scope",
    "plan_from_dict",
    "plan_to_dict",
    "resolve_project_llm",
    "run_task",
    "submit_task",
    "task_change_scope",
]
