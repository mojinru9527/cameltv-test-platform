"""AUD-013：A0 Orchestrator Agent（产出任务计划 Draft，不直接执行写操作）。

A0 的职责是任务分解 / 路由 / 状态 / 审批 / 上下文传递；**不能**直接执行任意业务写操作，
也不能批准 Contract / Workflow / 关闭缺陷。真正的 DAG 执行在
``app.aiqe.agents.orchestrator.run_plan``。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.aiqe.agents.protocol import AgentContext, AgentResult, stable_hash

AGENT_VERSION = "1.1.0"


class OrchestratorAgent:
    key = "A0"
    version = AGENT_VERSION
    model = "rule-based"

    def __init__(
        self, llm: Callable[[str, str], str] | None = None, *, model: str | None = None
    ) -> None:
        self._llm = llm
        if model:
            self.model = model

    def execute(self, context: AgentContext, request: str) -> AgentResult:
        from app.aiqe.agents.orchestrator import build_plan

        goal = str(request or "").strip()
        if not goal:
            return AgentResult(
                agent_key=self.key,
                agent_version=self.version,
                status="FAILED",
                error_code="GOAL_REQUIRED",
                model_name=self.model,
            )
        plan = build_plan(goal)
        ordered = plan.order()
        output: dict[str, Any] = {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "task_plan": [
                {
                    "task_id": task.task_id,
                    "agent_key": task.agent_key,
                    "depends_on": list(task.depends_on),
                    "max_attempts": task.max_attempts,
                    "timeout_seconds": task.timeout_seconds,
                    "allowed_tools": list(task.allowed_tools),
                }
                for task in ordered
            ],
            "a0_state": "QUEUED",
            "note": "A0 完成只代表计划任务完成，不代表产品 PASS；产品结论由 Assertion/Quality Gate 计算",
        }
        return AgentResult(
            agent_key=self.key,
            agent_version=self.version,
            status="COMPLETED",
            output=output,
            model_name=self.model,
            input_hash=stable_hash(goal),
            output_hash=stable_hash(output),
            prompt_version=stable_hash(self.version),
        )


__all__ = ["AGENT_VERSION", "OrchestratorAgent"]
