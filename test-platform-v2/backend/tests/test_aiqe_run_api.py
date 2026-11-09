"""M1 / TA-008：Run Console 只读 API 测试。"""
from __future__ import annotations

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.run import TestRun
from app.aiqe.services.event_service import append_event


def _seed(db, project_id: int = 1, key: str = "RUN-20261110-00001"):
    run = TestRun(project_id=project_id, run_key=key, source_type="manual", status="RUNNING")
    db.add(run)
    db.flush()
    append_event(
        db,
        run_id=run.id,
        event_type="run.started",
        payload={"schema_version": "1.0"},
        producer="system",
        producer_event_id=f"{key}-1",
    )
    db.add(
        RunArtifact(
            run_id=run.id,
            artifact_type="log",
            storage_uri="file:///tmp/not-used.log",
            sha256="0" * 64,
            size_bytes=10,
            mime_type="text/plain",
        )
    )
    db.commit()
    return run


def test_list_runs(client, auth_headers, db_session):
    run = _seed(db_session)
    client.headers.update(auth_headers)
    resp = client.get("/api/v1/aiqe/runs")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert any(item["id"] == run.id for item in data["items"])


def test_run_detail_events_artifacts(client, auth_headers, db_session):
    run = _seed(db_session)
    client.headers.update(auth_headers)

    detail = client.get(f"/api/v1/aiqe/runs/{run.id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()["data"]
    assert body["run"]["run_key"] == run.run_key
    assert body["events"][0]["seq"] == 1
    assert body["artifacts"][0]["artifact_type"] == "log"

    events = client.get(f"/api/v1/aiqe/runs/{run.id}/events", params={"after_seq": 0})
    assert events.status_code == 200
    assert events.json()["data"]["items"][0]["event_type"] == "run.started"

    artifacts = client.get(f"/api/v1/aiqe/runs/{run.id}/artifacts")
    assert artifacts.status_code == 200


def test_cross_project_run_is_404(client, auth_headers, db_session):
    run = _seed(db_session, project_id=2, key="RUN-OTHER-0001")
    client.headers.update(auth_headers)
    assert client.get(f"/api/v1/aiqe/runs/{run.id}").status_code == 404
    assert client.get(f"/api/v1/aiqe/runs/{run.id}/events").status_code == 404


def test_sse_once_stream(client, auth_headers, db_session):
    run = _seed(db_session)
    client.headers.update(auth_headers)
    resp = client.get(
        f"/api/v1/aiqe/runs/{run.id}/events/stream", params={"once": "1", "after_seq": 0}
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "data: " in resp.text
    assert "run.started" in resp.text


def test_missing_run_404(client, auth_headers):
    client.headers.update(auth_headers)
    assert client.get("/api/v1/aiqe/runs/no-such-run").status_code == 404


def test_event_occurred_order_not_required_but_seq_is(client, auth_headers, db_session):
    run = _seed(db_session)
    client.headers.update(auth_headers)
    resp = client.get(f"/api/v1/aiqe/runs/{run.id}/events", params={"after_seq": 1})
    assert resp.status_code == 200
    assert resp.json()["data"]["items"] == []
    assert resp.json()["data"]["last_seq"] == 1
