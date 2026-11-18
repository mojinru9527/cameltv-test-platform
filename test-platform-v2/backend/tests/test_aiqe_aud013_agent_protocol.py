"""AUD-013：统一 A0–A6 编号 / Agent Protocol / AgentResult / Orchestrator DAG 验收测试。

对应 v1.5 §03 AUD-013「验收」：
- A1→A2→A3 真正串行执行，子任务可追溯 AgentExecution / 模型 / Prompt / 工具调用；
- 人工暂停（WAITING_HUMAN）时下游取消并保留原因；
- 连续调用相同任务不重复执行（idempotency key）；
- Agent 不能调用未授权 Agent / 工具，也不能执行受保护动作。
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.aiqe.agents.learning_curator_agent import LearningCuratorAgent
from app.aiqe.agents.orchestrator import (
    AgentPlan,
    AgentTask,
    PlanError,
    build_plan,
    run_plan,
)
from app.aiqe.agents.orchestrator_agent import OrchestratorAgent
from app.aiqe.agents.protocol import (
    AgentContext,
    AgentContractError,
    AgentResult,
    ToolNotAllowed,
    stable_hash,
)
from app.aiqe.agents.registry import (
    ALLOWED_CHILDREN,
    FORBIDDEN_TOOLS,
    AgentRegistryError,
    assert_child_allowed,
    build_tool_registry,
    get_agent,
    registered_keys,
    tool_allowlist_for,
)
from app.aiqe.models.agent import AgentExecution


# ── 1. 协议与 AgentResult ────────────────────────────────
def test_agent_result_requires_all_traceability_fields():
    result = AgentResult(
        agent_key="A1",
        agent_version="1.1.0",
        status="COMPLETED",
        output={"summary": "ok"},
        model_provider="deepseek",
        model_name="deepseek-chat",
        prompt_version="sha256:abc",
        input_hash=stable_hash("in"),
        output_hash=stable_hash({"summary": "ok"}),
        token_usage={"input": 10, "output": 5},
    )
    payload = result.payload()
    for key in (
        "agent_key",
        "agent_version",
        "status",
        "output",
        "source_refs",
        "tool_calls",
        "model_provider",
        "model_name",
        "prompt_version",
        "input_hash",
        "output_hash",
        "token_usage",
        "warnings",
        "needs_human",
    ):
        assert key in payload


def test_agent_result_contract_violations():
    with pytest.raises(AgentContractError):
        AgentResult(agent_key="A1", agent_version="1", status="COMPLETED").validate()
    with pytest.raises(AgentContractError):
        AgentResult(agent_key="", agent_version="1", status="COMPLETED", output={"a": 1}).validate()
    with pytest.raises(AgentContractError):
        AgentResult(agent_key="A1", agent_version="1", status="DONE", output={"a": 1}).validate()
    with pytest.raises(AgentContractError):
        AgentResult(
            agent_key="A1", agent_version="1", status="COMPLETED", output={"a": 1}, needs_human=True
        ).validate()
    with pytest.raises(AgentContractError):
        AgentResult(agent_key="A1", agent_version="1", status="WAITING_HUMAN").validate()


# ── 2. Registry / 调用关系 / 工具 allowlist ──────────────
def test_registry_covers_a0_to_a6():
    assert registered_keys() == ("A0", "A1", "A2", "A3", "A4", "A5", "A6")
    assert get_agent("A1").key == "A1"
    assert get_agent("A0").key == "A0"
    assert get_agent("A6").key == "A6"
    with pytest.raises(AgentRegistryError):
        get_agent("A9")


def test_requirement_agent_is_a1_not_a0():
    assert get_agent("A1").key == "A1"
    assert get_agent("A0").__class__.__name__ == "OrchestratorAgent"


def test_child_call_relationships_enforced():
    assert_child_allowed("A0", "A1")
    with pytest.raises(AgentRegistryError):
        assert_child_allowed("A2", "A4")
    with pytest.raises(AgentRegistryError):
        assert_child_allowed("A9", "A1")
    # 受保护动作不能作为子任务
    assert "close_defect" in FORBIDDEN_TOOLS
    with pytest.raises(AgentRegistryError):
        assert_child_allowed("A0", "close_defect")


def test_tool_allowlist_denies_unlisted_tools():
    tools = build_tool_registry({"read_requirements": lambda **_: {"ok": True}})
    assert "read_requirements" in tools.allowed("A1")
    tools.resolve("A1", "read_requirements")
    with pytest.raises(ToolNotAllowed):
        tools.resolve("A1", "read_git_diff")  # 只允许 A5
    with pytest.raises(ToolNotAllowed):
        tools.resolve("A1", "execute_sql")
    with pytest.raises(ToolNotAllowed):
        tools.resolve("A1", "read_project_context")  # 允许但未注册实现 → 仍然 fail closed


# ── 3. 计划 DAG ─────────────────────────────────────────
def test_build_plan_orders_a1_a2_a3_serially():
    plan = build_plan("分析体育赛事需求并准备可执行测试")
    order = [task.agent_key for task in plan.order()]
    assert order.index("A1") < order.index("A2") < order.index("A3")
    assert order.index("A4") < order.index("A6")


def test_plan_rejects_cycle_missing_dependency_and_bad_agent():
    with pytest.raises(PlanError):
        AgentPlan(
            plan_id="p",
            goal="g",
            tasks=(
                AgentTask(task_id="t1", agent_key="A1", depends_on=("t2",)),
                AgentTask(task_id="t2", agent_key="A2", depends_on=("t1",)),
            ),
        ).order()
    with pytest.raises(PlanError):
        AgentPlan(
            plan_id="p", goal="g", tasks=(AgentTask(task_id="t1", agent_key="A1", depends_on=("x",)),)
        ).order()
    with pytest.raises(PlanError):
        AgentTask(task_id="t1", agent_key="A3", allowed_tools=("read_git_diff",)).validate()
    with pytest.raises(PlanError):
        build_plan("")


# ── 4. run_plan：执行 / 人工暂停 / 幂等 ──────────────────
def _project(db):
    from app.models.project import Project

    project = Project(id=1, code="agents", name="Agents", owner_id=1, status=1)
    db.add(project)
    db.commit()
    return project


def _fake_executor(behaviour):
    calls: list[str] = []

    def _execute(task: AgentTask, context: AgentContext, request: str) -> AgentResult:
        calls.append(task.agent_key)
        return behaviour(task, context, request)

    _execute.calls = calls  # type: ignore[attr-defined]
    return _execute


def test_run_plan_serial_execution_persists_traceability(db_session):
    _project(db_session)
    plan = build_plan("准备体育赛事用例", include=("a1_requirement", "a2_test_design", "a3_workflow"))

    def behaviour(task, context, request):
        return AgentResult(
            agent_key=task.agent_key,
            agent_version="1.1.0",
            status="COMPLETED",
            output={"draft": task.task_id},
            source_refs=[f"req:{task.task_id}"],
            tool_calls=[{"tool": "read_requirements", "args_hash": "h"}],
            model_provider="deepseek",
            model_name="deepseek-chat",
            prompt_version="sha256:prompt",
            input_hash=stable_hash(request),
            output_hash=stable_hash({"draft": task.task_id}),
            token_usage={"input": 12, "output": 7},
        )

    executor = _fake_executor(behaviour)
    result = run_plan(db_session, plan, project_id=1, executor=executor)
    db_session.commit()

    assert result.status == "COMPLETED"
    assert executor.calls == ["A1", "A2", "A3"]  # type: ignore[attr-defined]
    rows = list(db_session.scalars(select(AgentExecution).order_by(AgentExecution.created_at)))
    assert [row.agent_key for row in rows] == ["A1", "A2", "A3"]
    first = rows[0]
    assert first.agent_version == "1.1.0"
    assert first.model_provider == "deepseek"
    assert first.prompt_version == "sha256:prompt"
    assert first.input_hash.startswith("sha256:")
    assert first.output_hash.startswith("sha256:")
    assert first.token_usage_json == {"input": 12, "output": 7}
    assert first.source_refs_json == ["req:a1_requirement"]
    assert first.tool_calls_json
    assert first.task_id == "a1_requirement"


def test_run_plan_waiting_human_cancels_downstream(db_session):
    _project(db_session)
    plan = build_plan("需求有歧义", include=("a1_requirement", "a2_test_design", "a3_workflow"))

    def behaviour(task, context, request):
        if task.agent_key == "A1":
            return AgentResult(
                agent_key="A1",
                agent_version="1.1.0",
                status="WAITING_HUMAN",
                needs_human=True,
                warnings=["P0 AC 存在歧义，需要人工澄清"],
                output={"ambiguities": ["实时 = ?"]},
            )
        return AgentResult(
            agent_key=task.agent_key, agent_version="1.1.0", status="COMPLETED", output={"ok": 1}
        )

    result = run_plan(db_session, plan, project_id=1, executor=_fake_executor(behaviour))
    db_session.commit()
    assert result.status == "WAITING_HUMAN"
    assert result.waiting_human == ["a1_requirement"]
    assert result.tasks["a2_test_design"]["status"] == "CANCELLED"
    assert result.tasks["a2_test_design"]["reason"].startswith("PLAN_STOPPED")
    assert result.tasks["a3_workflow"]["status"] == "CANCELLED"


def test_run_plan_is_idempotent_with_key(db_session):
    _project(db_session)
    plan = build_plan("幂等", include=("a1_requirement",))
    calls = {"n": 0}

    def behaviour(task, context, request):
        calls["n"] += 1
        return AgentResult(
            agent_key=task.agent_key,
            agent_version="1.1.0",
            status="COMPLETED",
            output={"draft_id": "D-1"},
        )

    first = run_plan(db_session, plan, project_id=1, executor=_fake_executor(behaviour), idempotency_prefix="plan-1")
    second = run_plan(db_session, plan, project_id=1, executor=_fake_executor(behaviour), idempotency_prefix="plan-1")
    db_session.commit()
    assert calls["n"] == 1
    assert second.tasks["a1_requirement"]["reused"] is True
    assert first.tasks["a1_requirement"]["execution_id"]


def test_run_plan_failure_stops_plan_and_records_error(db_session):
    _project(db_session)
    plan = build_plan("失败", include=("a1_requirement", "a2_test_design"))

    def behaviour(task, context, request):
        if task.agent_key == "A1":
            return AgentResult(
                agent_key="A1",
                agent_version="1.1.0",
                status="FAILED",
                error_code="SCHEMA_INVALID",
                warnings=["bad json"],
            )
        return AgentResult(
            agent_key=task.agent_key, agent_version="1.1.0", status="COMPLETED", output={"ok": 1}
        )

    result = run_plan(db_session, plan, project_id=1, executor=_fake_executor(behaviour))
    db_session.commit()
    assert result.status == "FAILED"
    assert result.tasks["a2_test_design"]["status"] == "CANCELLED"
    rows = list(db_session.scalars(select(AgentExecution)))
    assert rows[0].status in {"failed", "FAILED"}


def test_run_plan_agent_exception_is_contained(db_session):
    _project(db_session)
    plan = build_plan("异常", include=("a1_requirement",))

    def behaviour(task, context, request):
        raise RuntimeError("provider exploded")

    result = run_plan(db_session, plan, project_id=1, executor=_fake_executor(behaviour))
    db_session.commit()
    assert result.status == "FAILED"
    assert "provider exploded" in result.errors[0]
    row = db_session.scalar(select(AgentExecution))
    assert row.status == "FAILED"
    assert "provider exploded" in row.error_text


# ── 5. A0 / A6 真实实现 ─────────────────────────────────
def test_orchestrator_agent_returns_plan_without_business_write():
    agent = OrchestratorAgent(None)
    context = AgentContext(project_id=1)
    result = agent.execute(context, "分析需求并准备测试")
    assert result.status == "COMPLETED"
    assert result.output["task_plan"]
    assert result.output["note"].startswith("A0 完成只代表")
    assert {item["agent_key"] for item in result.output["task_plan"]} >= {"A1", "A2", "A3"}


def test_learning_curator_requires_sources_and_human_approval():
    agent = LearningCuratorAgent(None)
    missing = agent.execute(AgentContext(project_id=1), "缺陷 1")
    assert missing.status == "FAILED"
    assert missing.error_code == "MODEL_UNAVAILABLE"

    llm = lambda system, user: (  # noqa: E731
        '{"pattern_key":"LIVE_ENTRY_OVERLAY","description":"浮层遮挡直播入口",'
        '"conditions":["integration profile"],"source_refs":["defect:1"],'
        '"false_positive_risk":"LOW","rationale":"历史缺陷复现"}'
    )
    agent = LearningCuratorAgent(llm)
    result = agent.execute(AgentContext(project_id=1), "缺陷 1")
    assert result.status in {"COMPLETED", "PARTIAL"}
    assert result.output["activation"] == "REQUIRES_BENCHMARK_AND_HUMAN_APPROVAL"
    assert result.output["auto_activated"] is False
    assert result.source_refs == ["defect:1"]


def test_learning_curator_rejects_missing_source_refs():
    llm = lambda system, user: '{"pattern_key":"X","description":"d","source_refs":[]}'  # noqa: E731
    result = LearningCuratorAgent(llm).execute(AgentContext(project_id=1), "缺陷 1")
    assert result.status == "FAILED"
    assert result.error_code == "SCHEMA_INVALID"
