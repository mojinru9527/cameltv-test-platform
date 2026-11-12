"""M3 / TA-021：A3 Workflow Planner（13 号 §19 TA-021）。

- 输出 Workflow Graph（nodes/edges/run_policy），必须通过 Workflow Validator；
- 依赖关系可由 `dependencies_match()` 与已标注业务工作流比对（20 个样本集）；
- 规划结果 `approval_status="pending"`：**未批准不能执行**（`ensure_executable` 强制）。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError, BaseAgent
from app.aiqe.services.capability_registry import known_capabilities
from app.aiqe.services.workflow_validator import WorkflowValidationError, validate_workflow

DEFAULT_DRIVERS = frozenset(
    {"http", "playwright", "db", "event", "mobile", "miniapp", "device", "external_e2e"}
)


class WorkflowNotApproved(RuntimeError):
    pass


class PlannedWorkflow(BaseModel):
    schema_version: str = "1.0"
    scenario_key: str = Field(min_length=1)
    nodes: list[dict[str, Any]] = Field(min_length=1)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    run_policy: dict[str, Any] = Field(
        default_factory=lambda: {"max_parallel_nodes": 3, "fail_fast": False}
    )


class WorkflowPlan(BaseModel):
    workflow: PlannedWorkflow
    rationale: str = ""
    approval_required: bool = True
    approval_status: str = "pending"


class WorkflowPlannerAgent(BaseAgent):
    key = "A3"
    model = "deepseek-chat"
    system_prompt = (
        "你是工作流规划 Agent。基于需求/验收标准输出严格 JSON："
        '{"workflow":{"schema_version":"1.0","scenario_key":str,"nodes":[...],"edges":[...],'
        '"run_policy":{...}},"rationale":str}。节点必须声明 key/driver/depends_on；'
        "依赖必须无环且变量只能引用祖先节点输出；不得自行批准。"
        "nodes[].driver 只能取 http/playwright/db/event/mobile/miniapp/device/external_e2e，不得使用角色名。"
    )

    def __init__(self, llm, *, registered_drivers=None, registered_capabilities=None) -> None:
        super().__init__(llm)
        self.registered_drivers = set(registered_drivers or DEFAULT_DRIVERS)
        self.registered_capabilities = (
            set(registered_capabilities) if registered_capabilities is not None else set(known_capabilities())
        )

    def validate(self, data: dict) -> dict:
        try:
            plan = WorkflowPlan.model_validate(data)
        except ValidationError as exc:
            raise AgentSchemaError(f"工作流规划 schema 校验失败: {exc}") from exc
        if plan.approval_status != "pending" or not plan.approval_required:
            raise AgentSchemaError("规划结果必须为待审批（不得自行批准）")
        try:
            validate_workflow(
                plan.workflow.model_dump(),
                registered_drivers=self.registered_drivers,
                registered_capabilities=self.registered_capabilities,
            )
        except WorkflowValidationError as exc:
            raise AgentSchemaError(f"工作流校验失败: {exc}") from exc
        return plan.model_dump()

    def plan(self, assessment: dict[str, Any], *, scenario_key: str | None = None) -> dict:
        payload = {"assessment": assessment, "scenario_key": scenario_key or ""}
        return self.run(str(payload))

    @staticmethod
    def dependencies_match(
        workflow: dict[str, Any], expected: dict[str, list[str]]
    ) -> bool:
        nodes = {node["key"]: node for node in workflow.get("nodes", [])}
        for key, deps in expected.items():
            node = nodes.get(key)
            if node is None or set(node.get("depends_on") or []) != set(deps):
                return False
        return True

    @staticmethod
    def ensure_executable(workflow_record: dict[str, Any]) -> None:
        if workflow_record.get("approval_status") != "approved":
            raise WorkflowNotApproved(
                f"工作流未批准，禁止执行: {workflow_record.get('approval_status')}"
            )
