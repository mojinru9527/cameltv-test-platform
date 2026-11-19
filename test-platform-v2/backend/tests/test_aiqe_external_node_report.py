"""batch-347c：外部 runner 回报回写 AIQE 节点 + 进程内消费者只认领 http。"""
from __future__ import annotations

import json

from sqlalchemy import select

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.models.execution_job import ExecutionJob


def _graph(driver: str) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "n1",
                "driver": driver,
                "input": {"url": "http://stub.local", "expect_text": "X"},
            }
        ],
        "edges": [],
    }


def _seed(db, driver: str, key: str, *, with_policy: bool = True):
    if with_policy:
        # V16-001：外部 runner 上报同样受服务端策略约束。
        from app.aiqe.security import upsert_target_policy

        upsert_target_policy(
            db,
            project_id=1,
            environment_id=None,
            policy={"allowed_hosts": ["stub.local"], "allowed_ports": [80, 443]},
        )
    graph = _graph(driver)
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="QUEUED")
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    dag_scheduler.schedule(
        db, run.id, graph, dispatch=lambda row: enqueue_node_run(db, row, graph=graph)
    )
    db.commit()
    job = db.scalar(select(ExecutionJob).where(ExecutionJob.status == "pending"))
    # V16-005：模拟外部节点认领（node_id/attempt/fencing token 必须与上报一致）。
    job.status = "running"
    job.node_id = "node-ext"
    job.attempt = 1
    db.commit()
    return run, job


def test_external_report_without_policy_blocks_even_if_runner_claims_success(db_session):
    """V16-001：策略是服务端不变量，外部 Runner 伪造 PASSED 也必须收口为 BLOCKED。"""
    run, job = _seed(db_session, "appium", "RUN-EXT-NOPOLICY", with_policy=False)
    out = job_consumer.complete_from_report(
        db_session,
        job_id=job.id,
        status="success",
        result={"status": "PASSED", "source_len": 100},
        fencing_token=1,
        node_id="node-ext",
    )
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    assert out["node_status"] == "BLOCKED"
    assert node.status == "BLOCKED"
    assert node.error_class == "TARGET_POLICY_MISSING_BINDING"
    assert run.outcome != "PASS"


def test_payload_contains_driver_and_input(db_session):
    _run, job = _seed(db_session, "appium", "RUN-EXT-0001")
    payload = json.loads(job.payload_json)
    assert payload["driver"] == "appium"
    assert payload["input"]["expect_text"] == "X"
    assert payload["graph"]["nodes"][0]["key"] == "n1"


def test_inprocess_consumer_skips_non_http(db_session):
    _seed(db_session, "appium", "RUN-EXT-0002")
    assert job_consumer.claim_aiqe_jobs(db_session) == []


def test_external_report_completes_node_success(db_session):
    run, job = _seed(db_session, "appium", "RUN-EXT-0003")
    out = job_consumer.complete_from_report(
        db_session,
        job_id=job.id,
        status="success",
        result={"status": "PASSED", "source_len": 100, "data": {"body_text": "X"}},
        fencing_token=1,
        node_id="node-ext",
    )
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    assert out["node_status"] == "PASSED"
    assert node.status == "PASSED"
    assert run.status == "COMPLETED" and run.outcome == "PASS"
    attempts = list(
        db_session.scalars(select(StepAttempt).where(StepAttempt.node_run_id == node.id))
    )
    assert [a.status for a in attempts] == ["PASSED"]


def test_external_report_failure_marks_node(db_session):
    run, job = _seed(db_session, "playwright", "RUN-EXT-0004")
    out = job_consumer.complete_from_report(
        db_session,
        job_id=job.id,
        status="failed",
        result={"status": "FAILED", "error_class": "OVERLAY_INTERCEPTED"},
        error_message="overlay",
        fencing_token=1,
        node_id="node-ext",
    )
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    assert out["error_class"] == "OVERLAY_INTERCEPTED"
    assert node.status == "FAILED"
    assert node.error_class == "OVERLAY_INTERCEPTED"
    assert run.outcome == "FAIL"
