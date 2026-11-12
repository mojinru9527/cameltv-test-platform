"""batch-339（P1）：平台矩阵真实数据 + SSE 长连接帧/断线续传测试。"""
from __future__ import annotations

from app.aiqe.models.run import TestRun
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.event_service import append_event
from app.aiqe.services.platform_matrix import build_platform_matrix


def _seed_nodes(db) -> None:
    register_manifest(
        db,
        node_id="node-web-1",
        driver_key="playwright",
        driver_version="1.50",
        capabilities=["browser.chromium", "browser.a11y"],
        platforms=["web", "h5"],
        evidence_ref="evidence://node-web-1",
    )
    register_manifest(
        db,
        node_id="node-android-1",
        driver_key="appium",
        driver_version="2.0",
        capabilities=["browser.chromium", "device.android"],
        platforms=["android"],
        evidence_ref="",  # 无 evidence → available=False
    )
    db.commit()


def test_matrix_empty(db_session) -> None:
    matrix = build_platform_matrix(db_session)
    assert matrix["platforms"] == []
    assert matrix["rows"] == []
    assert matrix["available_nodes"] == 0


def test_matrix_real_nodes(db_session) -> None:
    _seed_nodes(db_session)
    matrix = build_platform_matrix(db_session)

    assert matrix["platforms"] == ["android", "h5", "web"]
    assert matrix["available_nodes"] == 1

    rows = {row["capability"]: row["cells"] for row in matrix["rows"]}
    assert rows["browser.chromium"]["web"]["node_count"] == 1
    assert rows["browser.chromium"]["web"]["nodes"] == ["node-web-1"]
    assert rows["browser.chromium"]["android"]["available"] is False
    assert rows["device.android"]["android"]["node_count"] == 0


def test_platform_matrix_api(client, auth_headers, db_session) -> None:
    _seed_nodes(db_session)
    client.headers.update(auth_headers)
    resp = client.get("/api/v1/aiqe/platform-matrix")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["available_nodes"] == 1
    assert "browser.chromium" in data["capabilities"]


def _seed_run(db, key: str = "RUN-SSE-00001") -> TestRun:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="RUNNING")
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
    append_event(
        db,
        run_id=run.id,
        event_type="node.started",
        payload={"schema_version": "1.0", "node": "n1"},
        producer="system",
        producer_event_id=f"{key}-2",
    )
    db.commit()
    return run


def test_sse_frames_have_id_and_retry(client, auth_headers, db_session) -> None:
    run = _seed_run(db_session)
    client.headers.update(auth_headers)

    resp = client.get(f"/api/v1/aiqe/runs/{run.id}/events/stream", params={"once": 1})
    assert resp.status_code == 200
    assert "id: 1\n" in resp.text
    assert "retry: 3000\n" in resp.text
    assert "run.started" in resp.text
    assert "node.started" in resp.text


def test_sse_resumes_from_last_event_id(client, auth_headers, db_session) -> None:
    run = _seed_run(db_session, key="RUN-SSE-00002")
    client.headers.update(auth_headers)

    resp = client.get(
        f"/api/v1/aiqe/runs/{run.id}/events/stream",
        params={"once": 1},
        headers={"Last-Event-ID": "1"},
    )
    assert resp.status_code == 200
    assert "node.started" in resp.text
    assert "run.started" not in resp.text
    assert "id: 2\n" in resp.text


def test_platform_matrix_requires_permission(db_session) -> None:
    from app.models.project import Project, ProjectMember
    from app.models.rbac import Role
    from app.models.user import User
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from fastapi.testclient import TestClient

    role = Role(code="viewer", name="只读", data_scope="project")
    db_session.add(role)
    db_session.flush()
    user = User(id=9, username="viewer-m", password="x", nickname="V", email="v@v.local", status=1)
    project = Project(id=9, code="matrix-proj", name="Matrix", owner_id=9, status=1)
    db_session.add_all([user, project])
    db_session.flush()
    db_session.add(ProjectMember(project_id=9, user_id=9, role_id=role.id))
    db_session.commit()

    def _current_user() -> CurrentUser:
        return CurrentUser(
            user=db_session.get(User, 9),
            permissions=["defect:list"],
            project_id=9,
            system_permissions=["defect:list"],
        )

    app.dependency_overrides[get_db] = lambda: (yield db_session)
    app.dependency_overrides[get_current_user] = _current_user
    try:
        resp = TestClient(app).get("/api/v1/aiqe/platform-matrix")
        assert resp.status_code == 403, resp.text
    finally:
        app.dependency_overrides.clear()
