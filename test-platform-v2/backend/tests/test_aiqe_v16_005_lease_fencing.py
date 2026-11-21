"""V16-005 验收：租约 / fencing / 幂等 / Reconciler 状态机。

覆盖规格 §V16-005：
- 每次 claim 产生单调 fencing token；写结果必须携带 token；
- 重复投递/重复 dispatch 不产生第二个 Job 或第二个副作用；
- 旧 Worker 迟到结果被拒绝（STALE_LEASE），过期租约上报被拒绝（LEASE_EXPIRED）；
- QUEUED 长时间没有 Job 必须收敛并留下事件；
- Reconciler 重复执行幂等。
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import dag_scheduler, job_consumer, lease, reconciler
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.models.execution_job import ExecutionJob
from app.models.project import Project


def _ensure_schema(db) -> None:
    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="V16L", name="V16 Lease", owner_id=1, status=1))
        db.flush()
    upsert_target_policy(
        db,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["stub.local"], "allowed_ports": [80, 443]},
    )


def _graph(driver: str = "appium") -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "n1",
                "driver": driver,
                "depends_on": [],
                "input": {"url": "http://stub.local", "expect_text": "X"},
                "assertions": [
                    {
                        "assertion_key": "ok",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-1",
                        "type": "text_contains",
                        "expected": "X",
                        "severity": "P0",
                    }
                ],
            }
        ],
        "edges": [],
    }


def _seed(db, *, key: str, driver: str = "appium"):
    _ensure_schema(db)
    graph = _graph(driver)
    run = TestRun(project_id=1, run_key=key, status="QUEUED")
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    job = enqueue_node_run(db, db.scalar(select(NodeRun).where(NodeRun.run_id == run.id)), graph=graph)
    db.commit()
    node = db.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    return run, node, job


def _simulate_claim(db, job: ExecutionJob, node: NodeRun, *, token: int = 1, lease_seconds: int = 300):
    """模拟外部 Runner claim（node_id + attempt + fencing token + lease）。"""
    now = datetime.now(UTC)
    job.status = "running"
    job.node_id = "node-ext"
    job.attempt = int(token)
    job.claimed_at = now
    job.started_at = now
    job.heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=lease_seconds)
    node.status = "RUNNING"
    node.fencing_token = int(token)
    db.commit()


def _report(db, job, *, token: int, node_id: str = "node-ext", status: str = "success"):
    return job_consumer.complete_from_report(
        db,
        job_id=job.id,
        status=status,
        result={"status": "PASSED", "data": {"body_text": "X"}},
        fencing_token=token,
        node_id=node_id,
    )


# ── 1. 重复投递：只有一个终态 Attempt，后续上报幂等跳过 ────
def test_duplicate_delivery_is_idempotent(db_session):
    run, node, job = _seed(db_session, key="RUN-V16-L-1")
    _simulate_claim(db_session, job, node, token=1)

    first = _report(db_session, job, token=1)
    assert first["node_status"] == "PASSED", first

    skipped = []
    for _ in range(10):
        outcome = _report(db_session, job, token=1)
        assert outcome["skipped"] is True
        assert outcome["reason"] == "JOB_ALREADY_TERMINAL"
        skipped.append(outcome["reason"])
    assert len(skipped) == 10

    attempts = list(
        db_session.scalars(select(StepAttempt).where(StepAttempt.node_run_id == node.id))
    )
    terminal = [item for item in attempts if item.status in {"PASSED", "FAILED", "BLOCKED", "ERROR"}]
    assert len(terminal) == 1, [item.status for item in attempts]
    db_session.expire_all()
    assert db_session.get(NodeRun, node.id).status == "PASSED"


# ── 2. 旧 Worker 迟到结果被拒绝（fencing） ──────────────────
def test_stale_worker_result_rejected(db_session):
    run, node, job = _seed(db_session, key="RUN-V16-L-2")
    _simulate_claim(db_session, job, node, token=1)
    # 新 Worker 重新认领 → token 提升
    node.fencing_token = 5
    job.attempt = 5
    db_session.commit()

    outcome = _report(db_session, job, token=1)
    assert outcome["skipped"] is True
    assert outcome["reason"] == "STALE_LEASE"
    db_session.expire_all()
    assert db_session.get(NodeRun, node.id).status != "PASSED"
    from app.aiqe.services.event_service import list_events

    events = [event.event_type for event in list_events(db_session, run.id)]
    assert "security.fencing_rejected" in events


# ── 3. 过期租约上报被拒绝 ──────────────────────────────────
def test_expired_lease_report_rejected(db_session):
    run, node, job = _seed(db_session, key="RUN-V16-L-3")
    _simulate_claim(db_session, job, node, token=1)
    job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=5)
    db_session.commit()

    outcome = _report(db_session, job, token=1)
    assert outcome["skipped"] is True
    assert outcome["reason"] == "LEASE_EXPIRED"
    from app.aiqe.services.event_service import list_events

    events = [event.event_type for event in list_events(db_session, run.id)]
    assert "security.lease_expired" in events


# ── 4. Job 幂等：重复 dispatch 同一 Job；DB 唯一索引兜底 ────
def test_dispatch_is_idempotent_and_unique_index_enforced(db_session):
    run, node, job = _seed(db_session, key="RUN-V16-L-4")
    again = enqueue_node_run(db_session, node, graph=_graph())
    db_session.commit()
    assert again.id == job.id

    duplicate = ExecutionJob(
        project_id=1,
        kind="api",
        status="pending",
        payload_json=json.dumps({"run_id": run.id, "node_run_id": node.id}),
        run_id=run.id,
        node_run_id=node.id,
        execution_kind=job.execution_kind,
        attempt=job.attempt,
        idempotency_key=job.idempotency_key,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# ── 5. Reconciler：QUEUED 无 Job 收敛且幂等 ─────────────────
def test_reconciler_converges_queued_run_without_job(db_session):
    _ensure_schema(db_session)
    run = TestRun(project_id=1, run_key="RUN-V16-L-5", status="QUEUED")
    run.created_at = datetime.now(UTC) - timedelta(hours=2)
    db_session.add(run)
    db_session.flush()
    node = NodeRun(run_id=run.id, node_key="n1", driver_key="http", status="READY")
    db_session.add(node)
    db_session.commit()

    first = reconciler.reconcile(db_session, stale_seconds=60)
    db_session.commit()
    db_session.expire_all()
    run_row = db_session.get(TestRun, run.id)
    node_row = db_session.get(NodeRun, node.id)
    assert node_row.status in {"ERROR", "BLOCKED"}
    assert run_row.status in {"COMPLETED", "ERROR", "BLOCKED"}
    assert first.nodes_closed >= 1

    # 幂等：重复对账不产生新的状态变化或重复事件
    from app.aiqe.services.event_service import list_events

    before = len(list_events(db_session, run.id))
    second = reconciler.reconcile(db_session, stale_seconds=60)
    db_session.commit()
    after = len(list_events(db_session, run.id))
    assert second.nodes_closed == 0
    assert after == before, (before, after)


# ── 6. complete_node 直接写结果同样校验 token ───────────────
def test_complete_node_rejects_stale_token(db_session):
    _ensure_schema(db_session)
    run = TestRun(project_id=1, run_key="RUN-V16-L-6", status="RUNNING")
    db_session.add(run)
    db_session.flush()
    graph = _graph("http")
    dag_scheduler.create_node_runs(db_session, run.id, graph)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    node.fencing_token = 3
    db_session.commit()

    with pytest.raises(lease.StaleLeaseError):
        dag_scheduler.complete_node(
            db_session, run.id, node.node_key, "PASSED", graph, fencing_token=1
        )
    db_session.expire_all()
    assert db_session.get(NodeRun, node.id).status != "PASSED"
