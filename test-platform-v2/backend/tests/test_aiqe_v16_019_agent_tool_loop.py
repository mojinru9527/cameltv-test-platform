"""V16-019：Agent 工具调用闭环（ToolExecutor → BoundToolRegistry → 审计 → AgentResult）。

红线验证：
- Agent 只能通过 ToolExecutor 取证，越权工具直接拒绝；
- 真实调用会写 ToolExecutionAudit，并被写入 AgentResult.tool_calls；
- 只读工具读的是真实 DB / Git 事实，不是调用方传入的 Facts；
- 写工具保持 UNAVAILABLE。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select

from app.aiqe.agents.protocol import AgentContext
from app.aiqe.agents.registry import get_agent
from app.aiqe.agents.tool_executor import ToolExecutor
from app.aiqe.models.tool import ToolExecutionAudit
from app.aiqe.services import contract_service
from app.aiqe.services.tool_impls import READ_TOOLS, UNAVAILABLE_TOOLS
from app.aiqe.services.tool_registry import build_bound_registry
from app.models.project import Project

REPO_ROOT = Path(__file__).resolve().parents[3]


def _project(db, project_id: int = 1) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        project = Project(id=project_id, code=f"P{project_id}", name=f"Project {project_id}", owner_id=1, status=1)
        db.add(project)
        db.flush()
    return project


def _contract(db, project_id: int = 1, requirement_id: str = "favorite-match"):
    contract = contract_service.create_contract_draft(
        db,
        project_id=project_id,
        requirement_id=requirement_id,
        title="收藏赛事",
        source_refs=["prd:favorites-v1.md#收藏赛事"],
        acceptance_criteria=[
            {
                "ac_id": "AC-001",
                "given": "已登录",
                "when": "收藏赛事",
                "then": ["收藏成功"],
                "priority": "P1",
                "oracle_type": "REQ",
                "oracle_ref": "PRD:favorites",
            }
        ],
        created_by=1,
    )
    db.commit()
    return contract


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


# ── 1. 只读工具真实事实 ───────────────────────────────────
def test_read_requirements_returns_real_contracts(db_session):
    _project(db_session)
    contract = _contract(db_session)
    registry = build_bound_registry(db_session, project_id=1, actor_id=1)
    tool = registry.resolve("A1", "read_requirements")
    payload = tool()
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["contract_id"] == contract.id
    assert item["requirement_id"] == "favorite-match"
    assert item["acceptance_criteria"][0]["oracle_ref"] == "PRD:favorites"


def test_read_requirements_is_project_scoped(db_session):
    _project(db_session, 1)
    _project(db_session, 2)
    _contract(db_session, project_id=2, requirement_id="other-project")
    registry = build_bound_registry(db_session, project_id=1, actor_id=1)
    payload = registry.resolve("A1", "read_requirements")()
    assert payload["count"] == 0, payload


def test_read_git_diff_rejects_short_or_invalid_sha(db_session):
    _project(db_session)
    registry = build_bound_registry(db_session, project_id=1, actor_id=1)
    tool = registry.resolve("A5", "read_git_diff")
    with pytest.raises(Exception) as excinfo:
        tool(base_sha="abc123", head_sha="d" * 40)
    message = str(excinfo.value)
    assert "does not match" in message or "40" in message or "sha" in message.lower()


def test_read_git_diff_returns_server_derived_evidence(db_session):
    _project(db_session)
    head = _git("rev-parse", "HEAD")
    base = _git("rev-parse", "HEAD~1")
    registry = build_bound_registry(db_session, project_id=1, actor_id=1)
    payload = registry.resolve("A5", "read_git_diff")(base_sha=base, head_sha=head)
    assert payload["base_sha"] == base
    assert payload["head_sha"] == head
    assert payload["file_count"] >= 1
    assert payload["derived_by"].startswith("server:")
    assert isinstance(payload["analysis"], dict)


def test_write_tools_remain_unavailable():
    assert "create_regression_plan" in UNAVAILABLE_TOOLS
    assert "create_draft" in UNAVAILABLE_TOOLS
    assert "read_requirements" in READ_TOOLS
    assert "read_git_diff" in READ_TOOLS


# ── 2. ToolExecutor 授权 + 审计 + tool_calls ───────────────
def test_tool_executor_rejects_unauthorized_tool(db_session):
    _project(db_session)
    registry = build_bound_registry(db_session, project_id=1, actor_id=1)
    executor = ToolExecutor(registry=registry, agent_key="A4")
    with pytest.raises(PermissionError):
        executor.call("read_git_diff", base_sha="d" * 40, head_sha="e" * 40)
    # safe_call 不抛出，但显式返回拒绝原因
    result = executor.safe_call("read_git_diff", base_sha="d" * 40, head_sha="e" * 40)
    assert result["ok"] is False and "TOOL_NOT_ALLOWED" in result["error"]


def test_tool_executor_records_invocations_and_audits(db_session):
    _project(db_session)
    registry = build_bound_registry(db_session, project_id=1, actor_id=1, task_id="task-x")
    executor = ToolExecutor(registry=registry, agent_key="A1", task_id="task-x")
    assert "read_project_context" in executor.available()
    data = executor.call("read_project_context")
    assert data["project_id"] == 1
    calls = executor.tool_calls()
    assert calls and calls[0]["tool"] == "read_project_context" and calls[0]["ok"] is True
    audits = list(db_session.scalars(select(ToolExecutionAudit)))
    assert audits and audits[0].tool_name == "read_project_context"
    assert audits[0].task_id == "task-x"


# ── 3. Agent 真实消费 context.tool_executor ────────────────
def test_a1_agent_invokes_tools_through_executor(db_session):
    _project(db_session)
    _contract(db_session)
    seen_prompts: list[str] = []

    def stub_llm(system: str, prompt: str) -> str:
        seen_prompts.append(prompt)
        return json.dumps(
            {
                "summary": "收藏赛事需求清晰",
                "acceptance_criteria": [
                    {"id": "AC-1", "text": "收藏成功", "source_ref": "PRD:favorites#收藏赛事"}
                ],
                "risks": [],
            }
        )

    registry = build_bound_registry(db_session, project_id=1, actor_id=1, task_id="task-a1")
    executor = ToolExecutor(registry=registry, agent_key="A1", task_id="task-a1")
    context = AgentContext(project_id=1, tools=registry, tool_executor=executor)
    agent = get_agent("A1", stub_llm)
    result = agent.execute(context, "评估收藏赛事需求")

    assert result.status == "COMPLETED", result.warnings
    called = {item["tool"] for item in result.tool_calls}
    assert called == {"read_project_context", "read_requirements"}, called
    assert seen_prompts and "[TOOL_EVIDENCE]" in seen_prompts[0]
    assert "favorite-match" in seen_prompts[0]
    audits = list(db_session.scalars(select(ToolExecutionAudit)))
    assert {row.tool_name for row in audits} == {"read_project_context", "read_requirements"}


def test_a5_agent_reads_git_diff_when_shas_provided(db_session):
    _project(db_session)
    head = _git("rev-parse", "HEAD")
    base = _git("rev-parse", "HEAD~1")
    seen: list[str] = []

    def stub_llm(system: str, prompt: str) -> str:
        seen.append(prompt)
        return json.dumps({"impact_areas": [], "unknowns": [], "note": "stub"})

    registry = build_bound_registry(db_session, project_id=1, actor_id=1)
    executor = ToolExecutor(
        registry=registry,
        agent_key="A5",
        references={"base_sha": base, "head_sha": head},
    )
    context = AgentContext(project_id=1, tools=registry, tool_executor=executor)
    agent = get_agent("A5", stub_llm)
    agent.execute(context, "分析本次改动影响")
    called = {item["tool"] for item in executor.tool_calls()}
    assert "read_git_diff" in called, called


def test_get_agent_accepts_model_for_every_agent(db_session):
    """回归：get_agent(key, llm, model=...) 必须对 A0–A6 全部可用。

    审计后回归点：WorkflowPlannerAgent 曾不接受 model 参数，导致 run_plan 执行 A3
    直接 TypeError（生产 A3 永远无法通过 AgentTask 运行）。
    """
    from app.aiqe.agents.registry import get_agent

    def stub(system, prompt):
        return "{}"

    for key in ("A0", "A1", "A2", "A3", "A4", "A5", "A6"):
        agent = get_agent(key, stub, model="deepseek-chat")
        assert agent.key == key
