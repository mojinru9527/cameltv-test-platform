"""V16-013 验收：A0 AgentTask Draft → 审批 → 真实 run_plan 执行。

覆盖：
- Draft 不执行 Agent；
- 未审批 run 拒绝；
- 审批后每个 Plan 节点都有 AgentExecution 记录；
- Agent 失败 → Task 不得 COMPLETED，下游取消；
- A4 无 resolver → BLOCKED（V16-012 联动）；
- 取消/终态重跑/跨项目/计划篡改；
- Outbox + ExecutionJob 异步入口。
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.aiqe.agents.orchestrator import AgentPlan, build_plan
from app.aiqe.agents.protocol import AgentResult
from app.aiqe.models.agent import AgentExecution, AgentTask
from app.aiqe.services.agent_task_service import (
    AgentTaskError,
    approve_task,
    cancel_task,
    create_task,
    enqueue_task_job,
    execute_task_job,
    get_task,
    plan_to_dict,
    run_task,
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


def _executor(status: str = "COMPLETED", *, fail_keys: set[str] | None = None):
    def _run(task, context, request):
        failed = (fail_keys and task.agent_key in fail_keys) or status != "COMPLETED"
        return AgentResult(
            agent_key=task.agent_key,
            agent_version="1.0.0",
            status="FAILED" if failed else "COMPLETED",
            output={} if failed else {"note": "ok"},
            error_code="AGENT_FAILED" if failed else "",
        )

    return _run


def _task(db, *, include=("a1_requirement", "a2_test_design")):
    _project(db)
    return create_task(
        db,
        project_id=1,
        goal="分析体育赛事需求并准备测试",
        include=include,
        requested_by=10,
        idempotency_key=f"v16-013-{'-'.join(include)}",
    )


# ── 1. Draft 不执行 ───────────────────────────────────────
def test_draft_does_not_execute_agent(db_session):
    row = _task(db_session)
    assert row.status == "DRAFT"
    assert row.plan_hash.startswith("sha256:")
    executions = list(db_session.scalars(select(AgentExecution)))
    assert executions == []
    with pytest.raises(AgentTaskError) as exc:
        run_task(db_session, row.id, project_id=1, executor=_executor())
    assert exc.value.code == "APPROVAL_REQUIRED"


def test_approval_records_identity_and_rejects_plan_change(db_session):
    row = _task(db_session)
    with pytest.raises(AgentTaskError):
        approve_task(db_session, row.id, project_id=1, approved_by=None)
    with pytest.raises(AgentTaskError) as exc:
        approve_task(
            db_session,
            row.id,
            project_id=1,
            approved_by=2,
            expected_plan_hash="sha256:deadbeef",
        )
    assert exc.value.code == "PLAN_CHANGED"
    approved = approve_task(
        db_session, row.id, project_id=1, approved_by=2, reason="ok"
    )
    assert approved.status == "APPROVED"
    assert approved.approved_by == 2
    assert approved.approved_at is not None


# ── 2. 真实执行 plan + 每节点执行记录 ─────────────────────
def test_approved_run_executes_every_plan_node(db_session):
    row = _task(db_session)
    approve_task(db_session, row.id, project_id=1, approved_by=2)
    result = run_task(db_session, row.id, project_id=1, executor=_executor())
    assert result["task"]["status"] == "COMPLETED"
    executions = list(
        db_session.scalars(
            select(AgentExecution).where(AgentExecution.parent_task_id == row.id)
        )
    )
    assert {item.agent_key for item in executions} == {"A1", "A2"}
    assert all(item.status in {"COMPLETED", "succeeded"} for item in executions)
    assert result["task"]["result_refs"] == [item.id for item in executions]


def test_agent_failure_does_not_mark_task_completed(db_session):
    row = _task(db_session)
    approve_task(db_session, row.id, project_id=1, approved_by=2)
    result = run_task(
        db_session, row.id, project_id=1, executor=_executor(fail_keys={"A1"})
    )
    assert result["task"]["status"] == "FAILED"
    executions = list(
        db_session.scalars(
            select(AgentExecution).where(AgentExecution.parent_task_id == row.id)
        )
    )
    statuses = {item.agent_key: item.status for item in executions}
    assert statuses.get("A1") in {"FAILED", "failed"}
    assert "A2" not in statuses  # 依赖失败 → 下游未执行
    assert all(item.status not in {"COMPLETED", "succeeded"} for item in executions)


# ── 3. A4 resolver 联动：无 run_id → BLOCKED ───────────────
def test_a4_without_resolver_blocks_agent_task(db_session):
    row = _task(db_session, include=("a4_triage",))
    approve_task(db_session, row.id, project_id=1, approved_by=2)
    payload = {
        "execution_outcome": "FAIL",
        "attribution_status": "NEEDS_EXPERIMENT",
        "hypotheses": [
            {
                "classification": "PRODUCT_DEFECT",
                "summary": "x",
                "supporting_evidence": ["artifact:ghost"],
                "contradicting_evidence": [],
                "missing_evidence": ["e"],
                "recommended_experiment": "E1",
                "confidence": None,
                "status": "PROPOSED",
            }
        ],
        "human_review_required": True,
        "auto_close_defect": False,
    }
    result = run_task(
        db_session,
        row.id,
        project_id=1,
        llm=lambda system, user: json.dumps(payload),
    )
    assert result["task"]["status"] in {"BLOCKED", "FAILED"}
    executions = list(
        db_session.scalars(
            select(AgentExecution).where(AgentExecution.parent_task_id == row.id)
        )
    )
    assert executions and executions[0].status in {"BLOCKED", "blocked", "WAITING_HUMAN"}, [(e.agent_key, e.status, e.error_text[:200]) for e in executions]
    assert executions[0].needs_human is True


# ── 4. 取消 / 终态 / 跨项目 ───────────────────────────────
def test_cancel_and_terminal_rules(db_session):
    row = _task(db_session)
    canceled = cancel_task(db_session, row.id, project_id=1, reason="stop")
    assert canceled.status == "CANCELLED"
    with pytest.raises(AgentTaskError) as exc:
        cancel_task(db_session, row.id, project_id=1)
    assert exc.value.code == "ALREADY_TERMINAL"
    with pytest.raises(AgentTaskError):
        run_task(db_session, row.id, project_id=1, executor=_executor())


def test_cross_project_task_hidden(db_session):
    row = _task(db_session)
    _project(db_session, 2)
    with pytest.raises(AgentTaskError) as exc:
        get_task(db_session, row.id, project_id=2)
    assert exc.value.code == "TASK_NOT_FOUND"


# ── 5. Outbox + ExecutionJob 异步入口 ─────────────────────
def test_enqueue_and_execute_job(db_session):
    from app.aiqe.models.outbox import AIQEOutbox
    from app.models.execution_job import ExecutionJob

    row = _task(db_session)
    approve_task(db_session, row.id, project_id=1, approved_by=2)
    job = enqueue_task_job(db_session, row)
    db_session.commit()
    assert job.status == "pending"
    assert row.status == "QUEUED"
    events = list(
        db_session.scalars(
            select(AIQEOutbox).where(AIQEOutbox.event_type == "agent_task.queued")
        )
    )
    assert events

    result = execute_task_job(db_session, job.id, executor=_executor())
    db_session.commit()
    db_session.refresh(job)
    assert job.status == "success"
    assert result["task"]["status"] == "COMPLETED"
    assert db_session.get(ExecutionJob, job.id).result_json


def test_plan_serialization_roundtrip(db_session):
    plan = build_plan("goal", include=("a1_requirement", "a2_test_design"))
    payload = plan_to_dict(plan)
    from app.aiqe.services.agent_task_service import plan_from_dict

    restored = plan_from_dict(payload)
    assert isinstance(restored, AgentPlan)
    assert [task.task_id for task in restored.tasks] == [
        task.task_id for task in plan.tasks
    ]
    assert restored.tasks[1].depends_on == plan.tasks[1].depends_on
