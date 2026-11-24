"""AUD-013：A0 Orchestrator（任务计划 DAG / 人工暂停 / 工具 allowlist / 可追溯执行）。

v1.5 §03 AUD-013 实施要求：

1. A0 接收目标，建立唯一 ``AgentExecution`` 记录（每个子任务一条）；
2. 目标转成有向 Agent Task Plan，每个子任务有依赖、最大尝试、超时、允许工具；
3. 只能按 ``ALLOWED_CHILDREN`` 调度 A1…A6；
4. 人工审批暂停整条任务（``WAITING_HUMAN``），下游标记 CANCELLED 并保留原因；
5. 每步记录版本 / 模型 / Prompt / 工具调用 / 输入输出 hash / 异常；
6. 重试按阶段幂等（``idempotency_key`` 命中直接复用既有结果）。

Agent 永不改变执行事实、不批准 Workflow、不关闭缺陷——本模块只产出 Draft。
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.agents.base import BaseAgent
from app.aiqe.agents.protocol import (
    AgentContext,
    AgentResult,
    ToolRegistry,
    stable_hash,
)
from app.aiqe.agents.tool_executor import ToolExecutor
from app.aiqe.agents.registry import (
    ALLOWED_CHILDREN,
    AgentRegistryError,
    assert_child_allowed,
    build_tool_registry,
    get_agent,
    tool_allowlist_for,
)
from app.aiqe.models.agent import AgentExecution

PLAN_STATUSES: tuple[str, ...] = (
    "QUEUED",
    "RUNNING",
    "WAITING_HUMAN",
    "PARTIAL",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
)


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    agent_key: str
    depends_on: tuple[str, ...] = ()
    max_attempts: int = 1
    timeout_seconds: int = 300
    allowed_tools: tuple[str, ...] = ()
    input_refs: tuple[str, ...] = ()
    request: str = ""

    def validate(self) -> None:
        if not self.task_id or not self.agent_key:
            raise PlanError("task_id / agent_key 不能为空")
        if self.agent_key not in ALLOWED_CHILDREN:
            raise PlanError(f"未注册 Agent: {self.agent_key}")
        if self.max_attempts < 1:
            raise PlanError("max_attempts 必须 >= 1")
        if self.timeout_seconds < 1:
            raise PlanError("timeout_seconds 必须 >= 1")
        allowed = set(tool_allowlist_for(self.agent_key))
        illegal = set(self.allowed_tools) - allowed
        if illegal:
            raise PlanError(f"{self.agent_key} 无权使用工具: {sorted(illegal)}")


@dataclass(frozen=True)
class AgentPlan:
    plan_id: str
    goal: str
    tasks: tuple[AgentTask, ...] = ()

    def order(self) -> list[AgentTask]:
        by_id = {task.task_id: task for task in self.tasks}
        for task in self.tasks:
            task.validate()
            for dependency in task.depends_on:
                if dependency not in by_id:
                    raise PlanError(f"{task.task_id} 依赖不存在的任务: {dependency}")
                assert_child_allowed("A0", task.agent_key)
        ordered: list[AgentTask] = []
        visiting: set[str] = set()
        done: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in done:
                return
            if task_id in visiting:
                raise PlanError(f"任务计划存在环: {task_id}")
            visiting.add(task_id)
            for dependency in by_id[task_id].depends_on:
                visit(dependency)
            visiting.discard(task_id)
            done.add(task_id)
            ordered.append(by_id[task_id])

        for task in self.tasks:
            visit(task.task_id)
        return ordered


DEFAULT_PLAN_TEMPLATE: tuple[dict[str, Any], ...] = (
    {
        "task_id": "a1_requirement",
        "agent_key": "A1",
        "allowed_tools": ("read_project_context", "read_requirements", "read_openapi"),
    },
    {
        "task_id": "a2_test_design",
        "agent_key": "A2",
        "depends_on": ("a1_requirement",),
        "allowed_tools": ("read_requirements", "read_openapi", "create_draft"),
    },
    {
        "task_id": "a3_workflow",
        "agent_key": "A3",
        "depends_on": ("a2_test_design",),
        "allowed_tools": ("read_openapi", "create_draft"),
    },
    {
        "task_id": "a5_impact",
        "agent_key": "A5",
        "allowed_tools": ("read_git_diff", "read_defects", "create_regression_plan"),
    },
    {
        "task_id": "a4_triage",
        "agent_key": "A4",
        "allowed_tools": ("read_run_evidence", "read_defects", "create_draft"),
    },
    {
        "task_id": "a6_learning",
        "agent_key": "A6",
        "depends_on": ("a4_triage",),
        "allowed_tools": ("read_defects", "read_benchmark_dataset", "create_learning_candidate"),
    },
)


def build_plan(
    goal: str,
    *,
    include: tuple[str, ...] | None = None,
    plan_id: str | None = None,
) -> AgentPlan:
    """把目标拆成标准 A0→A6 任务计划（可按需裁剪子任务）。"""
    if not str(goal or "").strip():
        raise PlanError("goal 不能为空")
    selected = set(include) if include is not None else None
    tasks: list[AgentTask] = []
    for item in DEFAULT_PLAN_TEMPLATE:
        if selected is not None and item["task_id"] not in selected:
            continue
        tasks.append(
            AgentTask(
                task_id=str(item["task_id"]),
                agent_key=str(item["agent_key"]),
                depends_on=tuple(item.get("depends_on") or ()),
                allowed_tools=tuple(item.get("allowed_tools") or ()),
                request=f"{item['agent_key']} 任务：{goal}",
            )
        )
    return AgentPlan(plan_id=plan_id or f"plan-{uuid.uuid4().hex[:12]}", goal=str(goal), tasks=tuple(tasks))


@dataclass
class PlanRunResult:
    plan_id: str
    status: str
    goal: str
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    waiting_human: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def payload(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "goal": self.goal,
            "tasks": self.tasks,
            "waiting_human": list(self.waiting_human),
            "errors": list(self.errors),
        }


def _persist_execution(
    db: Session,
    *,
    project_id: int,
    task: AgentTask,
    context: AgentContext,
    status: str,
    request: str,
    result: AgentResult | None = None,
    error: str = "",
    run_id: str | None = None,
    idempotency_key: str | None = None,
) -> AgentExecution:
    row = AgentExecution(
        project_id=int(project_id),
        run_id=run_id,
        agent_key=task.agent_key,
        status=status,
        model=(result.model_name if result else ""),
        model_name=(result.model_name if result else ""),
        model_provider=(result.model_provider if result else ""),
        agent_version=(result.agent_version if result else "1.0.0"),
        prompt_version=(result.prompt_version if result else ""),
        input_text=request[:8000],
        input_hash=(result.input_hash if result else stable_hash(request)),
        output_hash=(result.output_hash if result else ""),
        output_json=(result.output if result else None),
        source_refs_json=(list(result.source_refs) if result else []),
        tool_calls_json=(list(result.tool_calls) if result else []),
        warnings_json=(list(result.warnings) if result else []),
        token_usage_json=(
            dict(result.token_usage) if result else {"input": 0, "output": 0}
        ),
        needs_human=bool(result.needs_human) if result else False,
        task_id=task.task_id,
        parent_task_id=context.extra.get("parent_task_id") if context.extra else None,
        idempotency_key=idempotency_key,
        error_text=error[:2000],
        finished_at=datetime.now(UTC) if status not in {"QUEUED", "RUNNING"} else None,
    )
    db.add(row)
    db.flush()
    return row


def _existing_execution(db: Session, idempotency_key: str) -> AgentExecution | None:
    return db.scalar(
        select(AgentExecution).where(
            AgentExecution.idempotency_key == idempotency_key,
            AgentExecution.status.in_(["succeeded", "COMPLETED"]),
        )
    )


def run_plan(
    db: Session,
    plan: AgentPlan,
    *,
    project_id: int,
    actor_id: int | None = None,
    llm: Callable[[str, str], str] | None = None,
    inputs: Mapping[str, str] | None = None,
    tools: ToolRegistry | None = None,
    executor: Callable[[AgentTask, AgentContext, str], AgentResult] | None = None,
    evidence_resolver: Callable[[list[str]], list[Any]] | None = None,
    idempotency_prefix: str | None = None,
    run_id: str | None = None,
    parent_task_id: str | None = None,
    extra_context: Mapping[str, Any] | None = None,
) -> PlanRunResult:
    """按 DAG 执行计划；人工暂停/失败会取消下游但保留已完成结果。"""
    ordered = plan.order()
    tool_registry = tools or build_tool_registry()
    extra_fields = {"parent_task_id": parent_task_id, "plan_id": plan.plan_id}
    extra_fields.update(dict(extra_context or {}))
    result = PlanRunResult(plan_id=plan.plan_id, status="RUNNING", goal=plan.goal)
    task_results: dict[str, AgentResult] = {}

    def _run_task(task: AgentTask) -> AgentResult:
        # V16-019：每个 AgentTask 绑定独立 ToolExecutor（真实 toolkit 授权 + 审计）。
        tool_executor = ToolExecutor(
            registry=tool_registry,
            agent_key=task.agent_key,
            task_id=task.task_id,
            references={"run_id": run_id, **dict(extra_context or {})},
        )
        context = AgentContext(
            project_id=int(project_id),
            actor_id=actor_id,
            run_id=run_id,
            idempotency_key=(
                f"{idempotency_prefix}:{task.task_id}" if idempotency_prefix else None
            ),
            tools=tool_registry,
            tool_executor=tool_executor,
            evidence_resolver=evidence_resolver,
            extra=dict(extra_fields),
        )
        if executor is not None:
            return executor(task, context, task.request)
        agent = get_agent(task.agent_key, llm)
        return agent.execute(context, inputs.get(task.task_id, task.request) if inputs else task.request)

    for task in ordered:
        if any(
            task_results.get(dep) is None or task_results[dep].status != "COMPLETED"
            for dep in task.depends_on
        ):
            result.tasks[task.task_id] = {
                "status": "CANCELLED",
                "reason": "DEPENDENCY_NOT_COMPLETED",
            }
            continue
        idempotency_key = (
            f"{idempotency_prefix}:{task.task_id}" if idempotency_prefix else None
        )
        if idempotency_key:
            existing = _existing_execution(db, idempotency_key)
            if existing is not None:
                reused = AgentResult(
                    agent_key=existing.agent_key,
                    agent_version=existing.agent_version,
                    status="COMPLETED",
                    output=dict(existing.output_json or {}),
                    source_refs=list(existing.source_refs_json or []),
                    tool_calls=list(existing.tool_calls_json or []),
                    model_provider=existing.model_provider,
                    model_name=existing.model_name,
                    prompt_version=existing.prompt_version,
                    input_hash=existing.input_hash,
                    output_hash=existing.output_hash,
                    token_usage=dict(existing.token_usage_json or {"input": 0, "output": 0}),
                    warnings=list(existing.warnings_json or []),
                )
                task_results[task.task_id] = reused
                result.tasks[task.task_id] = {
                    "status": "COMPLETED",
                    "reused": True,
                    "execution_id": existing.id,
                }
                continue

        started = time.monotonic()
        context = AgentContext(
            project_id=int(project_id),
            actor_id=actor_id,
            run_id=run_id,
            idempotency_key=idempotency_key,
            tools=tool_registry,
            tool_executor=ToolExecutor(
                registry=tool_registry,
                agent_key=task.agent_key,
                task_id=task.task_id,
                references={"run_id": run_id, **dict(extra_context or {})},
            ),
            evidence_resolver=evidence_resolver,
            extra=dict(extra_fields),
        )
        try:
            agent_result = _run_task(task)
        except AgentRegistryError as exc:
            result.errors.append(f"{task.task_id}: {exc}")
            _persist_execution(
                db,
                project_id=project_id,
                task=task,
                context=context,
                status="FAILED",
                request=task.request,
                error=str(exc),
                run_id=run_id,
                idempotency_key=idempotency_key,
            )
            task_results[task.task_id] = AgentResult(
                agent_key=task.agent_key,
                agent_version="1.0.0",
                status="FAILED",
                error_code="AGENT_NOT_AUTHORIZED",
            )
            result.tasks[task.task_id] = {"status": "FAILED", "error": str(exc)}
            result.status = "FAILED"
            break
        except Exception as exc:  # Agent 崩溃不能拖垮整条编排
            result.errors.append(f"{task.task_id}: {type(exc).__name__}: {exc}")
            _persist_execution(
                db,
                project_id=project_id,
                task=task,
                context=context,
                status="FAILED",
                request=task.request,
                error=f"{type(exc).__name__}: {exc}",
                run_id=run_id,
                idempotency_key=idempotency_key,
            )
            task_results[task.task_id] = AgentResult(
                agent_key=task.agent_key,
                agent_version="1.0.0",
                status="FAILED",
                error_code="AGENT_EXCEPTION",
            )
            result.tasks[task.task_id] = {
                "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            }
            result.status = "FAILED"
            break

        elapsed = time.monotonic() - started
        if elapsed > task.timeout_seconds:
            agent_result.warnings.append(f"AGENT_TIMEOUT: {elapsed:.1f}s > {task.timeout_seconds}s")
            agent_result.status = "FAILED"
            agent_result.error_code = "AGENT_TIMEOUT"
        try:
            agent_result.validate()
        except Exception as exc:
            result.errors.append(f"{task.task_id}: {exc}")
            _persist_execution(
                db,
                project_id=project_id,
                task=task,
                context=context,
                status="FAILED",
                request=task.request,
                result=agent_result,
                error=str(exc),
                run_id=run_id,
                idempotency_key=idempotency_key,
            )
            task_results[task.task_id] = agent_result
            result.tasks[task.task_id] = {"status": "FAILED", "error": str(exc)}
            result.status = "FAILED"
            break

        row = _persist_execution(
            db,
            project_id=project_id,
            task=task,
            context=context,
            status=(
                "WAITING_HUMAN"
                if agent_result.needs_human
                else ("succeeded" if agent_result.status == "COMPLETED" else agent_result.status.lower())
            ),
            request=task.request,
            result=agent_result,
            run_id=run_id,
            idempotency_key=idempotency_key,
        )
        task_results[task.task_id] = agent_result
        result.tasks[task.task_id] = {
            "status": agent_result.status,
            "execution_id": row.id,
            "needs_human": agent_result.needs_human,
            "source_refs": list(agent_result.source_refs),
        }
        if agent_result.needs_human:
            result.waiting_human.append(task.task_id)
            result.status = "WAITING_HUMAN"
            break
        if agent_result.status != "COMPLETED":
            result.status = "FAILED"
            break

    if result.status == "RUNNING":
        result.status = "COMPLETED"
    # 未执行的下游任务（人工暂停/失败/授权错误）必须显式取消并保留原因。
    stop_reason = f"PLAN_STOPPED:{result.status}"
    for task in ordered:
        if task.task_id not in result.tasks:
            result.tasks[task.task_id] = {"status": "CANCELLED", "reason": stop_reason}
    return result


def run_agent(
    db: Session,
    agent: BaseAgent,
    *,
    project_id: int,
    input_text: str,
    run_id: str | None = None,
) -> dict:
    """向后兼容入口：单 Agent 执行并落 ``AgentExecution``。"""
    started = datetime.now(UTC)
    row = AgentExecution(
        project_id=project_id,
        run_id=run_id,
        agent_key=agent.key,
        status="running",
        model=agent.model,
        input_text=input_text[:8000],
        input_hash=stable_hash(input_text),
        prompt_version=stable_hash(agent.system_prompt),
        agent_version="1.1.0",
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
    row.output_hash = stable_hash(output)
    row.finished_at = datetime.now(UTC)
    db.flush()
    return output


__all__ = [
    "DEFAULT_PLAN_TEMPLATE",
    "PLAN_STATUSES",
    "AgentPlan",
    "AgentTask",
    "PlanError",
    "PlanRunResult",
    "build_plan",
    "run_agent",
    "run_plan",
]
