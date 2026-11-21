"""V16-019 验收：Tool Registry 真实绑定、权限、schema、审批与审计。

覆盖：
- allowlist 每个工具存在实现或显式 UNAVAILABLE；
- 未注册/无实现/越权 Agent 拒绝；
- 只读工具返回真实 DB 事实并写审计；
- 额外字段/隐式 project 覆盖/敏感字段拒绝；
- 限流、超时；
- 写工具人工审批 + 生产环境只读；
- AgentTask 执行时注入真实绑定 registry。
"""
from __future__ import annotations

import time

import pytest
from sqlalchemy import select

from app.aiqe.agents.protocol import ToolNotAllowed
from app.aiqe.models.tool import ToolExecutionAudit
from app.aiqe.services.agent_task_service import approve_task, create_task, run_task
from app.aiqe.services.tool_registry import (
    BoundToolRegistry,
    ToolApprovalRequired,
    ToolPermissionError,
    ToolRateLimited,
    ToolSchemaError,
    ToolSpec,
    ToolTimeout,
    ToolUnavailable,
    build_bound_registry,
    default_specs,
    validate_implementations,
)
from app.models.project import Project


def _project(db, project_id: int = 1) -> None:
    if db.get(Project, project_id) is None:
        db.add(
            Project(
                id=project_id,
                code=f"P{project_id}",
                name=f"Project {project_id}",
                owner_id=1,
                status=1,
            )
        )
        db.flush()


def _registry(db, **overrides) -> BoundToolRegistry:
    _project(db)
    return build_bound_registry(
        db,
        project_id=1,
        actor_id=7,
        task_id="task-1",
        approval_token="task-1",
        **overrides,
    )


# ── 1. 启动校验 / allowlist ───────────────────────────────
def test_all_allowlist_tools_classified():
    report = validate_implementations()
    assert report["unavailable"] == [
        "create_draft",
        "create_learning_candidate",
        "create_regression_plan",
        "read_git_diff",
        "read_requirements",
    ]
    assert "read_project_context" in report["available"]


def test_unregistered_and_unavailable_rejected(db_session):
    registry = _registry(db_session)
    with pytest.raises(ToolNotAllowed):
        registry.resolve("A1", "read_project_context_unknown")
    with pytest.raises(ToolUnavailable):
        registry.resolve("A5", "read_git_diff")


def test_agent_without_permission_rejected(db_session):
    registry = _registry(db_session)
    with pytest.raises(ToolNotAllowed):
        registry.resolve("A1", "read_noise_rules")
    assert registry.resolve("A4", "read_noise_rules")


# ── 2. 只读工具真实执行 + 审计 ────────────────────────────
def test_read_tool_returns_real_project_and_writes_audit(db_session):
    registry = _registry(db_session)
    tool = registry.resolve("A1", "read_project_context")
    result = tool()
    assert result["project_id"] == 1
    assert result["name"] == "Project 1"
    db_session.flush()
    rows = list(db_session.scalars(select(ToolExecutionAudit)))
    assert len(rows) == 1
    assert rows[0].decision == "ALLOW"
    assert rows[0].tool_name == "read_project_context"
    assert rows[0].agent_key == "A1"
    assert rows[0].project_id == 1


def test_schema_extra_field_rejected_and_audited(db_session):
    registry = _registry(db_session)
    tool = registry.resolve("A1", "read_project_context")
    with pytest.raises(ToolSchemaError):
        tool(extra_field="x")
    rows = list(db_session.scalars(select(ToolExecutionAudit)))
    assert rows and rows[0].decision == "DENY"


def test_project_override_rejected(db_session):
    registry = _registry(db_session)
    tool = registry.resolve("A4", "read_defects")
    # 显式 project_id 属于额外字段/越权：schema 或权限层拒绝，不能覆盖绑定 Project。
    with pytest.raises((ToolPermissionError, ToolSchemaError)):
        tool(project_id=2)
    # 绑定 project 的调用正常
    result = tool(limit=5)
    assert result["project_id"] == 1


def test_secret_argument_rejected(db_session):
    specs = dict(default_specs())
    specs["read_project_context"] = ToolSpec(
        name="read_project_context",
        input_schema={"type": "object", "additionalProperties": True},
        handler=lambda db, project_id, **kwargs: {"ok": True},
    )
    registry = _registry(db_session, specs=specs)
    tool = registry.resolve("A1", "read_project_context")
    with pytest.raises(ToolSchemaError):
        tool(api_token="secret")


# ── 3. 限流 / 超时 ────────────────────────────────────────
def test_rate_limit_enforced(db_session):
    specs = dict(default_specs())
    specs["read_project_context"] = ToolSpec(
        name="read_project_context",
        input_schema={"type": "object", "additionalProperties": False},
        rate_limit_per_minute=1,
        handler=lambda db, project_id, **kwargs: {"ok": True},
    )
    registry = _registry(db_session, specs=specs)
    tool = registry.resolve("A1", "read_project_context")
    tool()
    with pytest.raises(ToolRateLimited):
        tool()


def test_timeout_enforced(db_session):
    def slow(db, project_id, **kwargs):
        time.sleep(0.3)
        return {"ok": True}

    specs = dict(default_specs())
    specs["read_project_context"] = ToolSpec(
        name="read_project_context",
        input_schema={"type": "object", "additionalProperties": False},
        timeout_seconds=0.05,
        handler=slow,
    )
    registry = _registry(db_session, specs=specs)
    with pytest.raises(ToolTimeout):
        registry.resolve("A1", "read_project_context")()


# ── 4. 写工具审批 / 生产只读 / 审计 ───────────────────────
def _write_specs():
    specs = dict(default_specs())
    specs["read_project_context"] = ToolSpec(
        name="read_project_context",
        input_schema={"type": "object", "additionalProperties": False},
        side_effect_level="WRITE",
        requires_human_approval=True,
        handler=lambda db, project_id, **kwargs: {"written": True},
    )
    return specs


def test_write_tool_requires_approval_token(db_session):
    registry = _registry(db_session, specs=_write_specs())
    tool = registry.resolve("A1", "read_project_context")
    with pytest.raises(ToolApprovalRequired):
        tool()
    assert tool(approval_token="task-1") == {"written": True}


def test_production_rejects_write_even_with_token(db_session):
    _project(db_session)
    registry = BoundToolRegistry(
        db=db_session,
        project_id=1,
        approval_token="task-1",
        specs=_write_specs(),
        environment="production",
    )
    with pytest.raises(ToolPermissionError):
        registry.resolve("A1", "read_project_context")(approval_token="task-1")


def test_deny_and_allow_audits_recorded(db_session):
    registry = _registry(db_session, specs=_write_specs())
    tool = registry.resolve("A1", "read_project_context")
    with pytest.raises(ToolApprovalRequired):
        tool()
    tool(approval_token="task-1")
    db_session.flush()
    decisions = [row.decision for row in db_session.scalars(select(ToolExecutionAudit))]
    assert "DENY" in decisions and "ALLOW" in decisions


# ── 5. AgentTask 注入真实 registry ────────────────────────
def test_agent_task_uses_bound_registry(db_session):
    _project(db_session)
    task = create_task(
        db_session,
        project_id=1,
        goal="goal",
        include=("a1_requirement",),
        requested_by=10,
        idempotency_key="v16-019-task",
    )
    approve_task(db_session, task.id, project_id=1, approved_by=2)

    def executor(plan_task, context, request):
        from app.aiqe.agents.protocol import AgentResult

        tool = context.tools.resolve("A1", "read_project_context")
        data = tool()
        return AgentResult(
            agent_key="A1",
            agent_version="1.0.0",
            status="COMPLETED",
            output={"project": data["project_id"]},
        )

    result = run_task(db_session, task.id, project_id=1, executor=executor)
    assert result["task"]["status"] == "COMPLETED"
    assert result["executions"][0]["status"] in {"COMPLETED", "succeeded"}
    audits = list(db_session.scalars(select(ToolExecutionAudit)))
    assert audits and audits[0].tool_name == "read_project_context"
    assert audits[0].task_id == task.id
