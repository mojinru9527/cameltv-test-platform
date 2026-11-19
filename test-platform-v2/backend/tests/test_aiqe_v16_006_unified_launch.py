"""V16-006 验收：唯一 Launch 服务 / LaunchResult / Outbox / Noise+Regression 真跑。

覆盖规格：
- Launch 返回 run_id/run_status/job_ids/node_run_ids/snapshot_hash/dispatch_status；
- 同幂等键重复请求返回同一 Run，不产生第二个 Job；
- Run/NodeRun/Job/Outbox 同事务写入；relay 幂等、失败可重试；
- Noise 实验与 Defect Regression 必须经统一 Launch，产生真实指向 Job，
  并且绑定冻结快照（回归保留全部 DAG 依赖）。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.aiqe.models.outbox import FAILED, PENDING, PUBLISHED, AIQEOutbox
from app.aiqe.models.run import TestRun
from app.aiqe.services import outbox_service
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.regression_service import (
    create_regression_request,
    record_deployment_attestation,
)
from app.aiqe.services.run_launch import LaunchResult, launch
from app.aiqe.services.snapshot_service import get_snapshot
from app.aiqe.services.triage_service import create_experiment, launch_experiment
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.defect import Defect
from app.models.execution_job import ExecutionJob
from app.models.project import Project

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "login",
            "driver": "http",
            "depends_on": [],
            "input": {"url": "https://api.test/login", "expected_status": 200},
            "assertions": [
                {
                    "assertion_key": "login_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-LOGIN",
                    "type": "http_status",
                    "expected": 200,
                    "severity": "P0",
                }
            ],
        },
        {
            "key": "order",
            "driver": "http",
            "depends_on": ["login"],
            "input": {"url": "https://api.test/orders", "expected_status": 201},
            "assertions": [
                {
                    "assertion_key": "order_ok",
                    "oracle_layer": "REQ",
                    "oracle_ref": "AC-ORDER",
                    "type": "http_status",
                    "expected": 201,
                    "severity": "P0",
                }
            ],
        },
    ],
    "edges": [{"from": "login", "to": "order"}],
    "run_policy": {"max_parallel_nodes": 2},
}


def _project(db) -> None:
    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="TEST", name="Test", owner_id=1, status=1))
        db.flush()
    register_manifest(
        db,
        node_id="node-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://node-http",
    )


def _workflow(db):
    _project(db)
    row = create_workflow(db, project_id=1, graph=GRAPH)
    approve_workflow(db, row.id, approved_by=1)
    db.flush()
    return row


def _jobs(db, run_id: str) -> list[ExecutionJob]:
    return list(
        db.scalars(
            select(ExecutionJob).where(ExecutionJob.run_id == run_id).order_by(ExecutionJob.id)
        )
    )


# ── 1. LaunchResult 契约 ───────────────────────────────────
def test_launch_result_contains_jobs_nodes_and_snapshot(db_session):
    workflow = _workflow(db_session)
    result = launch(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="v16-006-1",
    )
    assert isinstance(result, LaunchResult)
    assert result.run_id
    assert result.run_status in {"QUEUED", "RUNNING"}
    # DAG：order 依赖 login，首波只派发 login（有依赖的节点必须等上游完成）
    assert len(result.job_ids) == 1
    assert len(result.node_run_ids) == len(GRAPH["nodes"])
    assert len(result.snapshot_hash) == 64
    assert result.dispatch_status in {"DISPATCHED", "BLOCKED"}
    assert result.outbox_pending >= 1
    jobs = _jobs(db_session, result.run_id)
    assert [job.id for job in jobs] == list(result.job_ids)
    assert all(job.status == "pending" for job in jobs)


def test_launch_idempotency_key_returns_same_run_and_no_second_job(db_session):
    workflow = _workflow(db_session)
    first = launch(
        db_session, project_id=1, user_id=1, workflow_definition_id=workflow.id,
        launch_key="v16-006-idem",
    )
    second = launch(
        db_session, project_id=1, user_id=1, workflow_definition_id=workflow.id,
        launch_key="v16-006-idem",
    )
    assert second.run_id == first.run_id
    assert second.job_ids == first.job_ids
    assert len(_jobs(db_session, first.run_id)) == 1


# ── 2. Outbox：同事务 + relay 幂等 + 失败重试 ──────────────
def test_outbox_written_same_transaction_and_relay_idempotent(db_session):
    workflow = _workflow(db_session)
    result = launch(
        db_session, project_id=1, user_id=1, workflow_definition_id=workflow.id,
        launch_key="v16-006-outbox",
    )
    rows = list(db_session.scalars(select(AIQEOutbox).where(AIQEOutbox.run_id == result.run_id)))
    assert rows and all(row.status == PENDING for row in rows)
    assert {row.event_type for row in rows} >= {"run.dispatched"}

    first = outbox_service.relay(db_session)
    db_session.commit()
    assert first["published"] >= 1
    again = outbox_service.relay(db_session)
    db_session.commit()
    assert again["scanned"] == 0  # 幂等：已发布不再重复投递

    row = rows[0]
    db_session.refresh(row)
    assert row.status == PUBLISHED and row.published_at is not None


def test_outbox_relay_failure_retries_then_fails(db_session):
    _project(db_session)
    row = outbox_service.enqueue(
        db_session,
        project_id=1,
        event_type="run.dispatched",
        payload={"x": 1},
        producer_event_id="relay-fail-1",
    )
    db_session.commit()

    def _boom(_row):
        raise RuntimeError("queue down")

    report = outbox_service.relay(db_session, publisher=_boom)
    db_session.commit()
    assert report["failed"] == 1
    db_session.refresh(row)
    assert row.status == PENDING and row.attempts == 1
    assert "queue down" in row.last_error

    # 未到重试时间不重复消费
    early = outbox_service.relay(db_session, publisher=_boom)
    assert early["scanned"] == 0

    base = datetime.now(UTC) + timedelta(hours=1)
    for attempt in range(10):
        outbox_service.relay(db_session, publisher=_boom, now=base + timedelta(minutes=10 * attempt))
    db_session.commit()
    db_session.refresh(row)
    assert row.status == FAILED
    assert row.attempts >= outbox_service.MAX_ATTEMPTS


# ── 3. Noise 实验：真实 Run + Job + 快照 ──────────────────
def test_noise_experiment_launch_creates_real_jobs(db_session):
    workflow = _workflow(db_session)
    baseline = launch(
        db_session, project_id=1, user_id=1, workflow_definition_id=workflow.id,
        launch_key="v16-006-base",
    )
    experiment = create_experiment(
        db_session,
        experiment_key="E1",
        change={"run_attempt": 3},
        idempotency_key="v16-006-exp-1",
        baseline_run_id=baseline.run_id,
    )
    db_session.commit()
    launched = launch_experiment(db_session, experiment.id)
    db_session.commit()
    run = db_session.get(TestRun, launched.verification_run_id)
    assert run is not None
    assert run.execution_kind == "NOISE_EXPERIMENT"
    assert run.workflow_snapshot_id
    jobs = _jobs(db_session, run.id)
    assert len(jobs) == 1  # 首波只有无依赖节点
    assert all(job.id for job in jobs)
    snapshot = get_snapshot(db_session, run.workflow_snapshot_id, project_id=1)
    assert snapshot.canonical_json["edges"] == [{"from": "login", "to": "order"}]
    assert all(node["depends_on"] == ([] if node["key"] == "login" else ["login"]) for node in snapshot.canonical_json["nodes"])


# ── 4. Defect Regression：真实 Run + Job + 保留依赖 ───────
def test_regression_launch_creates_real_jobs_and_preserves_dag(db_session):
    workflow = _workflow(db_session)
    source = launch(
        db_session, project_id=1, user_id=1, workflow_definition_id=workflow.id,
        launch_key="v16-006-src",
    )
    defect = Defect(project_id=1, defect_id="BUG-1", title="order broken", severity="P1", status="open")
    db_session.add(defect)
    db_session.flush()
    sha = "a" * 40
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=sha, source="ci"
    )
    db_session.commit()

    row, run, created = create_regression_request(
        db_session,
        project_id=1,
        defect_id=defect.id,
        fixed_sha=sha,
        source_run_id=source.run_id,
        idempotency_key="v16-006-reg-1",
    )
    db_session.commit()
    assert created is True
    assert row.status in {"QUEUED", "RUNNING"}
    assert run is not None
    assert run.execution_kind == "DEFECT_REGRESSION"
    jobs = _jobs(db_session, run.id)
    assert len(jobs) == 1  # 首波只有无依赖节点
    snapshot = get_snapshot(db_session, run.workflow_snapshot_id, project_id=1)
    assert snapshot.canonical_json["edges"] == [{"from": "login", "to": "order"}]
    order_node = next(node for node in snapshot.canonical_json["nodes"] if node["key"] == "order")
    assert order_node["depends_on"] == ["login"]

    # 重复请求（同幂等键）返回既有回归与 Run，不创建第二个 Run
    again, again_run, created_again = create_regression_request(
        db_session,
        project_id=1,
        defect_id=defect.id,
        fixed_sha=sha,
        source_run_id=source.run_id,
        idempotency_key="v16-006-reg-1",
    )
    db_session.commit()
    assert created_again is False
    assert again.id == row.id
    assert again_run is not None and again_run.id == run.id


def test_regression_without_source_snapshot_is_blocked(db_session):
    _project(db_session)
    defect = Defect(project_id=1, defect_id="BUG-2", title="no snapshot", severity="P2", status="open")
    db_session.add(defect)
    db_session.flush()
    sha = "b" * 40
    record_deployment_attestation(
        db_session, project_id=1, environment_id=None, commit_sha=sha, source="ci"
    )
    source = TestRun(project_id=1, run_key="RUN-NO-SNAP", status="COMPLETED", outcome="FAIL")
    db_session.add(source)
    db_session.commit()

    row, run, created = create_regression_request(
        db_session, project_id=1, defect_id=defect.id, fixed_sha=sha,
        source_run_id=source.id, idempotency_key="v16-006-reg-2",
    )
    db_session.commit()
    assert created is True
    assert run is None
    assert row.status == "BLOCKED"
    assert any(item["code"] == "SOURCE_SNAPSHOT_MISSING" for item in (row.blockers_json or []))
