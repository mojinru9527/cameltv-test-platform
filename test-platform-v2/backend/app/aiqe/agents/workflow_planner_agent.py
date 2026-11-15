"""M3 / TA-021：A3 Workflow Planner（13 号 §19 TA-021）。

- 输出 Workflow Graph（nodes/edges/run_policy），必须通过 Workflow Validator；
- 依赖关系可由 `dependencies_match()` 与已标注业务工作流比对（20 个样本集）；
- 规划结果 `approval_status="pending"`：**未批准不能执行**（`ensure_executable` 强制）。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError, BaseAgent
from app.aiqe.schemas.contracts import ASSERTION_TYPES
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
        '"run_policy":{...}},"rationale":str}。'
        "每个节点必须是可执行 Runtime 契约："
        '{"key":str,"driver":"http|playwright|db|event|mobile|miniapp|device|external_e2e",'
        '"depends_on":[str],"input":{...},"assertions":[{...}]}。'
        "input 示例：http={url,method,timeout_ms}；playwright={url,actions:[{type,selector/text,expected}]}；"
        "db={query_key,allowed_tables,query_registry:{query_key:{sql,allowed_tables}}}。"
        "assertions 必须是 Runtime 支持类型："
        f"{sorted(ASSERTION_TYPES)}；每条断言必须含 assertion_key、type、oracle_layer(REQ|STD|PATTERN)、"
        "oracle_ref、expected/expected_ref。禁止只输出 steps/query/自定义断言。"
        "依赖必须无环且变量只能引用祖先节点输出；不得自行批准。"
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
        self._validate_runtime_ready(plan.workflow.model_dump())
        return plan.model_dump()

    @staticmethod
    def _validate_runtime_ready(workflow: dict[str, Any]) -> None:
        """A3 计划必须能直接进入 Runtime，而不是只过结构 Validator。

        Validator 只校验图结构；Runtime 还需要 driver 可消费的 input 与
        oracle-aware assertions。缺少这些字段的计划在审批后必然失败。
        """
        issues: list[str] = []
        for node in workflow.get("nodes") or []:
            key = str(node.get("key") or "?")
            driver = str(node.get("driver") or "")
            payload = node.get("input")
            if driver in {"http", "playwright", "db"}:
                if not isinstance(payload, dict) or not payload:
                    issues.append(f"[{key}] 缺少可执行 input")
                elif driver == "http" and not str(payload.get("url") or "").strip():
                    issues.append(f"[{key}] http.input.url 为空")
                elif driver == "playwright" and not str(payload.get("url") or "").strip():
                    issues.append(f"[{key}] playwright.input.url 为空")
                elif driver == "db" and not str(payload.get("query_key") or "").strip():
                    issues.append(f"[{key}] db.input.query_key 为空")
            assertions = node.get("assertions") or []
            if not isinstance(assertions, list) or not assertions:
                issues.append(f"[{key}] 至少需要 1 条 assertions")
                continue
            for index, assertion in enumerate(assertions):
                if not isinstance(assertion, dict):
                    issues.append(f"[{key}] assertions[{index}] 不是对象")
                    continue
                assertion_type = str(assertion.get("type") or "")
                if assertion_type == "exploratory":
                    continue
                if assertion_type not in ASSERTION_TYPES:
                    issues.append(f"[{key}] 不支持的 assertion type: {assertion_type!r}")
                if not str(assertion.get("assertion_key") or assertion.get("key") or "").strip():
                    issues.append(f"[{key}] assertion 缺少 assertion_key")
                if assertion.get("oracle_layer") not in {"REQ", "STD", "PATTERN"}:
                    issues.append(f"[{key}] assertion 缺少合法 oracle_layer")
                if not str(assertion.get("oracle_ref") or "").strip():
                    issues.append(f"[{key}] assertion 缺少 oracle_ref")
                if "expected" not in assertion and "expected_ref" not in assertion:
                    issues.append(f"[{key}] assertion 缺少 expected/expected_ref")
        if issues:
            raise AgentSchemaError("A3 计划不可直接执行: " + "; ".join(issues))

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
