"""M10-347：AIQE 进程内执行器 + ExecutionJob 消费者测试。"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.models.execution_job import ExecutionJob

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "api",
            "driver": "http",
            "input": {"url": "http://stub.local/health", "method": "GET", "expected_status": 200},
        }
    ],
    "edges": [],
}


@dataclass
class FakeResult:
    ok: bool
    status_code: int | None
    error: str | None = None
    duration_ms: int = 5
    request: dict = None
    response: dict = None

    def __post_init__(self):
        self.request = self.request or {"method": "GET", "url": "http://stub.local/health"}
        self.response = self.response or {"status_code": self.status_code}


def _seed_run(db, graph=GRAPH, key="RUN-EXEC-0001") -> tuple[TestRun, ExecutionJob]:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="QUEUED")
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    dag_scheduler.schedule(
        db, run.id, graph, dispatch=lambda row: enqueue_node_run(db, row, graph=graph)
    )
    db.commit()
    job = db.scalar(select(ExecutionJob).where(ExecutionJob.status == "pending"))
    return run, job


def _patch_http(monkeypatch, ok: bool, status_code: int = 200):
    monkeypatch.setattr(
        "app.aiqe.services.node_executor.HttpDriver.execute",
        lambda self, spec: FakeResult(ok=ok, status_code=status_code),
    )


def test_consumer_executes_http_node(db_session, monkeypatch):
    run, job = _seed_run(db_session)
    _patch_http(monkeypatch, ok=True)

    claimed = job_consumer.claim_aiqe_jobs(db_session)
    assert claimed == [job.id]
    out = job_consumer.run_job(db_session, job.id)

    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "PASSED"
    assert db_session.get(TestRun, run.id).outcome == "PASS"
    assert out["node_status"] == "PASSED"
    assert db_session.get(ExecutionJob, job.id).status == "success"
    attempts = list(
        db_session.scalars(select(StepAttempt).where(StepAttempt.node_run_id == node.id))
    )
    assert [a.status for a in attempts] == ["PASSED"]


def test_consumer_failure_marks_node_and_job(db_session, monkeypatch):
    run, job = _seed_run(db_session, key="RUN-EXEC-0002")
    _patch_http(monkeypatch, ok=False, status_code=500)

    job_consumer.claim_aiqe_jobs(db_session)
    job_consumer.run_job(db_session, job.id)

    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "FAILED"
    assert node.error_class == "STATUS_MISMATCH"
    assert db_session.get(TestRun, run.id).outcome == "FAIL"
    assert db_session.get(ExecutionJob, job.id).status == "failed"


def test_claim_is_idempotent(db_session):
    _seed_run(db_session, key="RUN-EXEC-0003")
    assert len(job_consumer.claim_aiqe_jobs(db_session)) == 1
    assert job_consumer.claim_aiqe_jobs(db_session) == []


def test_non_aiqe_job_not_claimed(db_session):
    db_session.add(
        ExecutionJob(project_id=1, kind="api", status="pending", payload_json='{"cases": []}')
    )
    db_session.commit()
    assert job_consumer.claim_aiqe_jobs(db_session) == []


def test_blocked_driver_marks_node_blocked(db_session, monkeypatch):
    graph = {
        "schema_version": "1.0",
        "nodes": [{"key": "ui", "driver": "iot", "input": {}}],
        "edges": [],
    }
    run, job = _seed_run(db_session, graph=graph, key="RUN-EXEC-0004")
    job_consumer.claim_aiqe_jobs(db_session)
    out = job_consumer.run_job(db_session, job.id)

    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    assert out["error_class"] == "UNSUPPORTED_DRIVER"
