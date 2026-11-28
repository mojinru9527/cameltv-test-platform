"""V16-018 / FIX-005：AgentTask **正式 API 入口** E2E（A0–A6 全链路）。

正式链路（本文件唯一断言对象）：

    POST /api/v1/aiqe/agent-tasks (submit=true)
      → POST /api/v1/aiqe/agent-tasks/{id}/approve（真实登录取证身份）
      → POST /api/v1/aiqe/agent-tasks/{id}/run（返回 job_id）
      → job_consumer.claim_agent_task_jobs（Worker 正式认领）
      → job_consumer.run_job（Worker 正式执行）
      → GET /api/v1/aiqe/agent-tasks/{id}（终态 + result_refs）

断言的真实产物：AgentExecution（每个 plan 节点）、ToolExecutionAudit
（BoundToolRegistry/ToolExecutor 真实调用）、A5 `read_git_diff` 带真实 base/head SHA、
ExecutionJob 终态。测试**不**直接调用 ``execute_task_job`` 推进主路径。

controlled_llm_test：模型调用是受控替换边界（monkeypatch
``agent_task_service.resolve_project_llm``），本文件证明生命周期/工具/审计/证据链，
**不是**生产模型质量结论。

证据边界：本文件是 ``platform`` 级（TC-PLATFORM-009）证据，不是产品 TC-AIQE-010 的
产品级 PASS；产品级 Benchmark/审批链见 ``docs/aiqe/v1.6/e2e/TC-AIQE-010-Benchmark-Evidence.md``。
"""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.aiqe.agents.protocol import AgentResult
from app.aiqe.models.agent import AgentExecution, AgentTask
from app.aiqe.models.run import TestRun as AgentTaskEvidenceRun
from app.aiqe.models.tool import ToolExecutionAudit
from app.aiqe.services import agent_task_service, job_consumer
from app.models.execution_job import ExecutionJob
from app.models.project import Project

BASE = "/api/v1/aiqe/agent-tasks"
FULL_PLAN = [
    "a1_requirement",
    "a2_test_design",
    "a3_workflow",
    "a4_triage",
    "a5_impact",
    "a6_learning",
]

pytestmark = pytest.mark.integration


# ── 真实提交对（A5 的 base/head SHA 必须来自真实 git 历史）────────────
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    ).stdout.strip()


def _repo_commit_pair() -> tuple[str, str]:
    try:
        head = _git("rev-parse", "HEAD")
        base = _git("rev-parse", "HEAD~1")
        changed = _git("diff", "--name-only", f"{base}..{head}")
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"BLOCKED: 无法解析真实 git 提交对（{exc}）")
    if len(base) != 40 or len(head) != 40 or not changed:
        pytest.skip("BLOCKED: 当前 checkout 没有非空 diff 的相邻提交，无法验证 A5 真实 SHA")
    return base, head


def _evidence_run(db) -> AgentTaskEvidenceRun:
    """证据锚点 Run（AgentTask 的 run_id 指向它，A4/A6 refs 由 resolver 校验）。"""
    run = AgentTaskEvidenceRun(
        id=str(uuid.uuid4()),
        project_id=1,
        run_key=f"e2e-agent-api-{uuid.uuid4().hex[:8]}",
        source_type="manual",
        status="COMPLETED",
        outcome="PASS",
        workflow_checksum="0" * 64,
    )
    db.add(run)
    db.flush()
    return run


def _stub_llm(evidence_ref: str):
    """controlled_llm_test：确定性模型输出（不含任何生产质量结论）。"""

    def llm(system: str, prompt: str) -> str:  # noqa: ARG001 - prompts 只做路由
        if "需求评估" in system:
            return json.dumps(
                {
                    "summary": "健康检查需求可测",
                    "acceptance_criteria": [
                        {"id": "AC-1", "text": "health 返回 200", "source_ref": "PRD:health#200"}
                    ],
                    "risks": [],
                }
            )
        if "测试设计" in system:
            return json.dumps(
                {
                    "decision": "approve",
                    "cases": [
                        {
                            "title": "health 200",
                            "priority": "P1",
                            "steps": ["GET /health"],
                            "acceptance_refs": ["AC-1"],
                        }
                    ],
                    "coverage_notes": "覆盖基本健康检查",
                    "reject_reason": "",
                    "duplicate_of": [],
                }
            )
        if "工作流规划" in system:
            # A3 只校验计划可执行性（不发起网络请求）；结构必须满足 Runtime 契约。
            return json.dumps(
                {
                    "workflow": {
                        "schema_version": "1.0",
                        "scenario_key": "e2e-agent-api",
                        "nodes": [
                            {
                                "key": "biz",
                                "driver": "http",
                                "depends_on": [],
                                "input": {
                                    "url": "http://127.0.0.1:9/health",
                                    "expected_status": 200,
                                },
                                "assertions": [
                                    {
                                        "assertion_key": "biz_business",
                                        "oracle_layer": "REQ",
                                        "oracle_ref": "AC-BIZ",
                                        "type": "jsonpath",
                                        "path": "$.success",
                                        "expected": True,
                                        "severity": "P0",
                                    }
                                ],
                            }
                        ],
                        "edges": [],
                    },
                    "rationale": "最小可执行工作流",
                    "approval_required": True,
                    "approval_status": "pending",
                }
            )
        if "变更影响" in system:
            return json.dumps(
                {
                    "impacted_areas": ["api"],
                    "candidate_suites": ["api-suite", "smoke-suite"],
                    "forced_suites": [],
                    "rationale": "由服务端 read_git_diff 证据推导",
                }
            )
        if "归因" in system:
            return json.dumps(
                {
                    "execution_outcome": "INCOMPLETE",
                    "attribution_status": "NEEDS_EXPERIMENT",
                    "hypotheses": [
                        {
                            "classification": "AUTOMATION",
                            "summary": "Runner 环境导致节点未完成",
                            "supporting_evidence": [evidence_ref],
                            "contradicting_evidence": [],
                            "missing_evidence": ["runner 日志"],
                            "recommended_experiment": "E1",
                            "confidence": None,
                            "confidence_band": "LOW",
                            "status": "PROPOSED",
                        }
                    ],
                    "human_review_required": True,
                    "auto_close_defect": False,
                }
            )
        if "BugPattern" in system:
            return json.dumps(
                {
                    "pattern_key": "runner-environment-flake",
                    "description": "Runner 环境不稳定导致节点未完成",
                    "conditions": ["node INCOMPLETE"],
                    "source_refs": [evidence_ref],
                    "false_positive_risk": "LOW",
                    "rationale": "来自真实 Run 证据",
                }
            )
        raise AssertionError(f"未覆盖的 Agent system prompt: {system[:80]}")

    return llm


def _executions(db, task_id: str) -> list[AgentExecution]:
    return list(
        db.scalars(
            select(AgentExecution)
            .where(AgentExecution.parent_task_id == task_id)
            .order_by(AgentExecution.created_at)
        )
    )


# ── 1. 正式入口全链路 ─────────────────────────────────────
def test_agent_task_api_full_chain(client, auth_headers, db_session, monkeypatch):
    """controlled_llm_test：POST→approve→run→claim→run_job→GET 全链路。"""
    base_sha, head_sha = _repo_commit_pair()
    run = _evidence_run(db_session)
    evidence_ref = f"run:{run.id}"
    monkeypatch.setattr(
        agent_task_service,
        "resolve_project_llm",
        lambda db, project_id: _stub_llm(evidence_ref),
    )

    created = client.post(
        BASE,
        headers=auth_headers,
        json={
            "goal": "分析业务并准备测试、影响面与学习候选",
            "include": FULL_PLAN,
            "run_id": run.id,
            "submit": True,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "repo": "cameltv-test-platform",
            "idempotency_key": f"e2e-api-{uuid.uuid4().hex[:8]}",
        },
    )
    assert created.status_code == 200, created.text
    payload = created.json()["data"]
    task_id = payload["task_id"]
    assert payload["status"] == "PENDING_APPROVAL", payload
    assert payload["approval_required"] is True
    assert payload["change_scope"]["base_sha"] == base_sha
    assert payload["change_scope"]["head_sha"] == head_sha
    assert {item["agent_key"] for item in payload["tasks"]} == {
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "A6",
    }

    # 未审批不得执行（API 层 fail-closed）
    early = client.post(f"{BASE}/{task_id}/run", headers=auth_headers)
    assert early.status_code == 409, early.text
    assert "APPROVAL_REQUIRED" in early.text

    approved = client.post(
        f"{BASE}/{task_id}/approve",
        headers=auth_headers,
        json={"reason": "E2E 审批", "expected_plan_hash": payload["plan_hash"]},
    )
    assert approved.status_code == 200, approved.text
    approved_data = approved.json()["data"]
    assert approved_data["status"] == "APPROVED"
    assert approved_data["approved_by"] == 1
    assert approved_data["approved_at"]

    queued = client.post(f"{BASE}/{task_id}/run", headers=auth_headers)
    assert queued.status_code == 202, queued.text
    job_id = int(queued.json()["data"]["job_id"])
    assert queued.json()["data"]["status"] == "QUEUED"

    claimed = job_consumer.claim_agent_task_jobs(db_session)
    assert claimed == [job_id], f"Worker 正式认领失败: {claimed}"
    result = job_consumer.run_job(db_session, job_id)
    db_session.commit()
    assert result["task"]["status"] == "COMPLETED", result

    final = client.get(f"{BASE}/{task_id}", headers=auth_headers)
    assert final.status_code == 200, final.text
    final_data = final.json()["data"]
    assert final_data["status"] == "COMPLETED"
    assert final_data["error_code"] == ""
    assert len(final_data["result_refs"]) == 6, final_data["result_refs"]

    executions = _executions(db_session, task_id)
    assert {item.agent_key for item in executions} == {"A1", "A2", "A3", "A4", "A5", "A6"}
    assert {item.id for item in executions} == set(final_data["result_refs"])
    declared = {
        item.agent_key: {call.get("tool") for call in (item.tool_calls_json or [])}
        for item in executions
    }
    assert "read_requirements" in declared["A1"]
    assert "read_git_diff" in declared["A5"]
    # SHA 已注入 A5 的输入/上下文（AgentExecution.input_text 可见）
    a5_row = next(item for item in executions if item.agent_key == "A5")
    assert base_sha in (a5_row.input_text or "")
    assert head_sha in (a5_row.input_text or "")

    audits = list(
        db_session.scalars(
            select(ToolExecutionAudit).where(ToolExecutionAudit.task_id == task_id)
        )
    )
    assert audits, "BoundToolRegistry 必须写 ToolExecutionAudit"
    assert {row.agent_key for row in audits} >= {"A1", "A2", "A4", "A5", "A6"}
    diff_audits = [
        row for row in audits if row.tool_name == "read_git_diff" and row.decision == "ALLOW"
    ]
    assert diff_audits, [(row.tool_name, row.decision) for row in audits]
    for audit in diff_audits:
        assert audit.args_summary_json.get("base_sha") == base_sha
        assert audit.args_summary_json.get("head_sha") == head_sha
    # 写工具在 AgentTask 执行中仍不可用：不得出现 ALLOW 的写工具审计
    assert not {
        row.tool_name
        for row in audits
        if row.decision == "ALLOW"
        and row.tool_name in {"create_draft", "create_learning_candidate"}
    }

    job = db_session.get(ExecutionJob, job_id)
    assert job is not None and job.status == "success"
    assert job.attempt == 1
    task_row = db_session.get(AgentTask, task_id)
    assert task_row.status == "COMPLETED"
    assert task_row.result_refs_json and len(task_row.result_refs_json) == 6


# ── 2. A5 缺 SHA 必须是 NOT_PROVEN（不得“无影响 PASS”）────────────
def test_agent_task_api_a5_without_sha_is_not_proven(
    client, auth_headers, db_session, monkeypatch
):
    """controlled_llm_test：A5-only 任务未提供 base/head → 任务 BLOCKED/A5_NOT_PROVEN。"""
    run = _evidence_run(db_session)
    evidence_ref = f"run:{run.id}"
    monkeypatch.setattr(
        agent_task_service,
        "resolve_project_llm",
        lambda db, project_id: _stub_llm(evidence_ref),
    )

    created = client.post(
        BASE,
        headers=auth_headers,
        json={
            "goal": "只做变更影响分析（缺少 SHA）",
            "include": ["a5_impact"],
            "run_id": run.id,
            "submit": True,
            "idempotency_key": f"e2e-api-a5-{uuid.uuid4().hex[:8]}",
        },
    )
    assert created.status_code == 200, created.text
    task_id = created.json()["data"]["task_id"]
    assert client.post(
        f"{BASE}/{task_id}/approve", headers=auth_headers, json={"reason": "e2e"}
    ).status_code == 200
    queued = client.post(f"{BASE}/{task_id}/run", headers=auth_headers)
    assert queued.status_code == 202, queued.text
    job_id = int(queued.json()["data"]["job_id"])
    assert job_consumer.claim_agent_task_jobs(db_session) == [job_id]
    job_consumer.run_job(db_session, job_id)
    db_session.commit()

    final = client.get(f"{BASE}/{task_id}", headers=auth_headers)
    assert final.status_code == 200, final.text
    data = final.json()["data"]
    assert data["status"] == "BLOCKED", data
    assert data["error_code"] == "A5_NOT_PROVEN", data
    executions = _executions(db_session, task_id)
    assert executions and executions[0].agent_key == "A5"
    assert executions[0].status == "BLOCKED"
    assert "A5_NOT_PROVEN" in list(executions[0].warnings_json or [])
    # 没有 SHA 就不会有 read_git_diff 审计（不伪造 diff 证据）
    assert not list(
        db_session.scalars(
            select(ToolExecutionAudit).where(
                ToolExecutionAudit.task_id == task_id,
                ToolExecutionAudit.tool_name == "read_git_diff",
            )
        )
    )


# ── 3. 入参/审批负向：单边 SHA、错误 plan hash、未审批入队 ─────────
def test_agent_task_api_rejects_incomplete_sha(client, auth_headers):
    resp = client.post(
        BASE,
        headers=auth_headers,
        json={
            "goal": "只给 base_sha",
            "include": ["a5_impact"],
            "base_sha": "a" * 40,
            "submit": True,
        },
    )
    assert resp.status_code == 400, resp.text
    assert "SHA_INCOMPLETE" in resp.text


def test_agent_task_api_rejects_plan_hash_mismatch(client, auth_headers):
    created = client.post(
        BASE,
        headers=auth_headers,
        json={"goal": "审批 hash 校验", "include": ["a1_requirement"], "submit": True},
    )
    assert created.status_code == 200, created.text
    task_id = created.json()["data"]["task_id"]
    resp = client.post(
        f"{BASE}/{task_id}/approve",
        headers=auth_headers,
        json={"expected_plan_hash": "sha256:deadbeef"},
    )
    assert resp.status_code == 400, resp.text
    assert "PLAN_CHANGED" in resp.text


def test_unapproved_task_cannot_be_enqueued_or_executed(db_session):
    """负向：DRAFT 任务既不能入队，也不能经 worker 执行推进状态。"""
    from app.aiqe.services.agent_task_service import (
        AgentTaskError,
        create_task,
        enqueue_task_job,
        execute_task_job,
    )

    if db_session.get(Project, 1) is None:
        db_session.add(Project(id=1, code="P1", name="P1", owner_id=1, status=1))
        db_session.flush()
    task = create_task(
        db_session,
        project_id=1,
        goal="未审批任务",
        include=("a1_requirement",),
        requested_by=10,
        idempotency_key="e2e-unapproved",
    )
    with pytest.raises(AgentTaskError) as exc:
        enqueue_task_job(db_session, task)
    assert exc.value.code == "APPROVAL_REQUIRED"
    assert db_session.get(AgentTask, task.id).status == "DRAFT"

    # 绕过 API 直接造 Job：worker 仍必须拒绝，且 Job 落 failed，不产生 AgentExecution。
    from app.models.execution_job import ExecutionJob

    job = ExecutionJob(
        project_id=1,
        kind="agent_task",
        status="pending",
        payload_json=json.dumps({"task_id": task.id, "project_id": 1}),
        case_refs_json=json.dumps([task.id]),
        idempotency_key=f"agent-task:{task.id}",
        execution_kind="AGENT_TASK",
    )
    db_session.add(job)
    db_session.flush()
    with pytest.raises(AgentTaskError):
        execute_task_job(db_session, job.id)
    db_session.commit()
    db_session.refresh(job)
    assert job.status == "failed"
    assert not _executions(db_session, task.id)


# ── 4. Worker 执行中的写工具边界（Agent 不能无审批写）───────────────
def test_write_tools_rejected_without_approval(db_session):
    from app.aiqe.services.tool_registry import (
        ToolApprovalRequired,
        ToolSpec,
        ToolUnavailable,
        build_bound_registry,
        default_specs,
    )

    if db_session.get(Project, 1) is None:
        db_session.add(Project(id=1, code="P1", name="P1", owner_id=1, status=1))
        db_session.flush()

    # 1) 生产默认：create_draft 没有真实实现 → 任何 Agent 都不能调用
    registry = build_bound_registry(
        db_session, project_id=1, actor_id=1, task_id="neg-task-1"
    )
    with pytest.raises(ToolUnavailable):
        registry.resolve("A2", "create_draft")

    # 2) 即使注入 WRITE 实现，没有审批 token 也必须拒绝并写 DENY 审计
    specs = dict(default_specs())
    specs["create_draft"] = ToolSpec(
        name="create_draft",
        side_effect_level="WRITE",
        requires_human_approval=True,
        handler=lambda db, project_id, **kwargs: {"created": True},
    )
    guarded = build_bound_registry(
        db_session, project_id=1, actor_id=1, task_id="neg-task-2", specs=specs
    )
    tool = guarded.resolve("A2", "create_draft")
    with pytest.raises(ToolApprovalRequired):
        tool()
    db_session.commit()
    audits = list(
        db_session.scalars(
            select(ToolExecutionAudit).where(ToolExecutionAudit.task_id == "neg-task-2")
        )
    )
    assert audits and audits[0].decision == "DENY"
    assert audits[0].side_effect_level == "WRITE"


# ── 5. Agent 工具失败不得声称完成（contract 级反向保证）──────────────
def test_agent_result_contract_rejects_empty_completed_output():
    from app.aiqe.agents.protocol import AgentContractError

    with pytest.raises(AgentContractError):
        AgentResult(
            agent_key="A5",
            agent_version="1.0.0",
            status="COMPLETED",
            output={},
        ).validate()
