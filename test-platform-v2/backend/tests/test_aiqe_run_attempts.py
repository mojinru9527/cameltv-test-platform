"""batch-340：节点 attempt 持久化 + 重试时间线 API 测试。"""
from __future__ import annotations

from sqlalchemy import select

from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.services import dag_scheduler

GRAPH = {
    "schema_version": "1.0",
    "retry": {"max_attempts": 2},
    "nodes": [{"key": "api", "driver": "http"}],
    "edges": [],
}

GRAPH_NO_RETRY = {
    "schema_version": "1.0",
    "nodes": [{"key": "api", "driver": "http"}],
    "edges": [],
}


def _start(db, graph=GRAPH, key: str = "RUN-ATT-0001") -> TestRun:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="QUEUED")
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    dag_scheduler.schedule(db, run.id, graph)
    db.commit()
    return run


def _node(db, run_id: str) -> NodeRun:
    return db.scalar(select(NodeRun).where(NodeRun.run_id == run_id))


def _attempts(db, run_id: str) -> list[StepAttempt]:
    node = _node(db, run_id)
    return list(
        db.scalars(
            select(StepAttempt)
            .where(StepAttempt.node_run_id == node.id)
            .order_by(StepAttempt.attempt_no)
        )
    )


def test_failed_attempt_kept_and_retry_runs(db_session):
    run = _start(db_session)
    dag_scheduler.mark_running(db_session, run.id, "api")
    dag_scheduler.complete_node(
        db_session, run.id, "api", "FAILED", GRAPH, error_class="HTTP_503"
    )
    db_session.commit()
    db_session.refresh(run)

    node = _node(db_session, run.id)
    assert run.status == "RUNNING"
    assert node.status == "PENDING"
    assert node.finished_at is None
    first = _attempts(db_session, run.id)
    assert len(first) == 1 and first[0].status == "FAILED"
    assert first[0].error_json == {"class": "HTTP_503"}

    dag_scheduler.schedule(db_session, run.id, GRAPH)
    dag_scheduler.mark_running(db_session, run.id, "api")
    dag_scheduler.complete_node(db_session, run.id, "api", "PASSED", GRAPH)
    db_session.commit()
    db_session.refresh(run)

    assert run.status == "COMPLETED" and run.outcome == "PASS"
    attempts = _attempts(db_session, run.id)
    assert [a.status for a in attempts] == ["FAILED", "PASSED"]
    assert [a.attempt_no for a in attempts] == [1, 2]


def test_no_retry_policy_keeps_failure(db_session):
    run = _start(db_session, graph=GRAPH_NO_RETRY, key="RUN-ATT-0002")
    dag_scheduler.mark_running(db_session, run.id, "api")
    dag_scheduler.complete_node(
        db_session, run.id, "api", "FAILED", GRAPH_NO_RETRY, error_class="HTTP_500"
    )
    db_session.commit()
    db_session.refresh(run)

    node = _node(db_session, run.id)
    assert node.status == "FAILED"
    assert run.status == "COMPLETED" and run.outcome == "FAIL"
    assert [a.status for a in _attempts(db_session, run.id)] == ["FAILED"]


def test_attempts_api_returns_timeline(client, auth_headers, db_session):
    run = _start(db_session, key="RUN-ATT-0003")
    dag_scheduler.mark_running(db_session, run.id, "api")
    dag_scheduler.complete_node(
        db_session, run.id, "api", "FAILED", GRAPH, error_class="HTTP_503"
    )
    db_session.commit()
    dag_scheduler.schedule(db_session, run.id, GRAPH)
    dag_scheduler.mark_running(db_session, run.id, "api")
    dag_scheduler.complete_node(db_session, run.id, "api", "PASSED", GRAPH)
    db_session.commit()

    client.headers.update(auth_headers)
    resp = client.get(f"/api/v1/aiqe/runs/{run.id}/attempts")
    assert resp.status_code == 200, resp.text
    item = resp.json()["data"]["items"][0]
    assert item["node_key"] == "api"
    assert item["attempt_count"] == 2
    assert [a["status"] for a in item["attempts"]] == ["FAILED", "PASSED"]
    assert item["attempts"][0]["error"] == {"class": "HTTP_503"}


def test_attempts_api_404(client, auth_headers):
    client.headers.update(auth_headers)
    resp = client.get("/api/v1/aiqe/runs/no-such-run/attempts")
    assert resp.status_code == 404, resp.text
