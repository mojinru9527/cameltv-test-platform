"""M10-347：AIQE 进程内执行器 + ExecutionJob 消费者测试。

AUD-001 起 http 节点统一经 ``SafeHttpExecutor``（服务端 Target Policy），
因此这里先落一条允许 ``stub.local`` 的项目级策略，再替换执行器结果。
"""
from __future__ import annotations

from sqlalchemy import select

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.security import SafeHttpResult, upsert_target_policy
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


def _seed_policy(db) -> None:
    upsert_target_policy(
        db,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["stub.local"],
            "allowed_ports": [80],
            "allowed_methods": ["GET"],
            "max_redirects": 0,
        },
    )


def _seed_run(db, graph=GRAPH, key="RUN-EXEC-0001") -> tuple[TestRun, ExecutionJob]:
    _seed_policy(db)
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
    def _fake(self, request, policy):
        return SafeHttpResult(
            ok=ok,
            status_code=status_code,
            duration_ms=5,
            request={"method": request.method, "url": request.url},
            response={"status_code": status_code},
            policy_version=policy.version,
        )

    monkeypatch.setattr(
        "app.aiqe.services.node_executor.SafeHttpExecutor.request", _fake
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
    # AUD-007：`expected_status` 会被转成 http.status 断言并由断言引擎判定，因此
    # error_class 是 ASSERTION_FAILED（引擎结论）而不是 Driver 的 STATUS_MISMATCH。
    assert node.error_class in {"STATUS_MISMATCH", "ASSERTION_FAILED"}
    assert db_session.get(TestRun, run.id).outcome == "FAIL"
    assert db_session.get(ExecutionJob, job.id).status == "failed"
    assertion_rows = list(
        db_session.scalars(
            select(RunAssertionResult)
            .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
            .where(StepAttempt.node_run_id == node.id)
        )
    )
    assert [row.assertion_key for row in assertion_rows] == ["http.status"]
    assert assertion_rows[0].status == "FAIL"


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
    job.status = "running"
    db_session.commit()
    out = job_consumer.run_job(db_session, job.id)

    db_session.expire_all()
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    # AUD-005：iot 是已声明但无可用节点的 driver，Preflight 在进入 Driver 前即 BLOCKED；
    # 若未来有节点注册而执行器仍不支持，则回落到 UNSUPPORTED_DRIVER —— 两者都必须是 BLOCKED。
    assert out["error_class"] in {"PREFLIGHT_BLOCKED", "UNSUPPORTED_DRIVER"}
    if out["error_class"] == "PREFLIGHT_BLOCKED":
        assert node.output_ref["preflight"]["blockers"][0]["code"] == "NO_CAPABLE_RUNNER"
