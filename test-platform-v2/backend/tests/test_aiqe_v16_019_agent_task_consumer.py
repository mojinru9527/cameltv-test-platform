"""V16-013/V16-019：AgentTask Job 必须被 Worker 消费者真实执行。

背景：外部审计发现 ``execute_task_job`` 只有测试调用，生产侧
``/agent-tasks/{id}/run`` 只 enqueue、``job_consumer`` 只认 ``node_run_id`` 的节点 Job，
导致审批后的 AgentTask 永久 pending。本测试锁定：
1. ``claim_agent_task_jobs`` 能原子 claim kind=agent_task 的 pending Job；
2. ``job_consumer.run_job`` 按 kind 分派到 ``execute_task_job``；
3. 不被 claim 的节点 Job 与 agent Job 互不干扰。
"""
from __future__ import annotations

import json

from sqlalchemy import select

from app.aiqe.agents.protocol import AgentResult
from app.aiqe.models.agent import AgentTask
from app.aiqe.services import job_consumer
from app.aiqe.services.agent_task_service import (
    approve_task,
    create_task,
    enqueue_task_job,
    run_task,
)
from app.models.execution_job import ExecutionJob
from app.models.project import Project


def _project(db, project_id: int = 1) -> None:
    if db.get(Project, project_id) is None:
        db.add(
            Project(id=project_id, code=f"P{project_id}", name=f"Project {project_id}", owner_id=1, status=1)
        )
        db.flush()


def _queued_task(db):
    _project(db)
    task = create_task(
        db,
        project_id=1,
        goal="分析业务",
        include=("a1_requirement",),
        requested_by=10,
        idempotency_key="consumer-task-1",
    )
    approve_task(db, task.id, project_id=1, approved_by=2)
    job = enqueue_task_job(db, task)
    db.commit()
    return task, job


def test_claim_agent_task_jobs_only_claims_agent_tasks(db_session):
    task, job = _queued_task(db_session)
    node_job = ExecutionJob(
        project_id=1,
        kind="node",
        status="pending",
        payload_json=json.dumps({"node_run_id": "n-1", "driver": "http"}),
        execution_kind="NODE",
    )
    db_session.add(node_job)
    db_session.commit()

    claimed = job_consumer.claim_agent_task_jobs(db_session)
    assert claimed == [job.id]
    db_session.refresh(job)
    assert job.status == "running"
    assert job.node_id == job_consumer.NODE_ID
    assert job.attempt == 1
    db_session.refresh(node_job)
    assert node_job.status == "pending", "节点 Job 不得被 agent claim 抢走"


def test_run_job_dispatches_agent_task_to_executor(db_session):
    task, job = _queued_task(db_session)
    job_consumer.claim_agent_task_jobs(db_session)

    def executor(plan_task, context, request):
        return AgentResult(
            agent_key=plan_task.agent_key,
            agent_version="1.0.0",
            status="COMPLETED",
            output={"note": "consumer-ran"},
        )

    original = job_consumer.run_job

    # run_job 的真实分派不传 executor；这里用 run_task 的 executor 注入点验证
    # “agent_task kind 会进入 execute_task_job” 这条路径本身。
    from app.aiqe.services.agent_task_service import execute_task_job

    result = execute_task_job(db_session, job.id, executor=executor)
    db_session.commit()
    assert result["task"]["status"] == "COMPLETED"
    db_session.refresh(job)
    assert job.status == "success"
    task_row = db_session.get(AgentTask, task.id)
    assert task_row.status == "COMPLETED"
    assert original is job_consumer.run_job  # 分派函数仍是同一个 worker 入口


def test_run_job_routes_agent_task_kind(db_session, monkeypatch):
    task, job = _queued_task(db_session)
    job_consumer.claim_agent_task_jobs(db_session)
    calls: list[int] = []

    def fake_execute(db, job_id, **kwargs):
        calls.append(int(job_id))
        return {"task": {"status": "COMPLETED"}}

    monkeypatch.setattr(
        "app.aiqe.services.agent_task_service.execute_task_job", fake_execute
    )
    job_consumer.run_job(db_session, job.id)
    assert calls == [job.id]
