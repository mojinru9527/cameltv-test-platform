"""batch-342（M9-3）：Workflow 写 API + 独立审批权限点测试。"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

GRAPH = {
    "schema_version": "1.0",
    "nodes": [{"key": "n1", "driver": "http"}],
    "edges": [],
}
GRAPH_V2 = {
    "schema_version": "1.0",
    "nodes": [
        {"key": "n1", "driver": "http"},
        {"key": "n2", "driver": "playwright", "depends_on": ["n1"]},
    ],
    "edges": [{"from": "n1", "to": "n2"}],
}


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="wf-writer", password="x", nickname="T", email="t@t.local", status=1)
    project = Project(id=1, code="wf-write", name="WF Write", owner_id=1, status=1)
    db.add_all([user, project])
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.commit()


def _make_client(db: Session, permissions: list[str]) -> TestClient:
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _override_db() -> Iterator[Session]:
        yield db

    def _current_user() -> CurrentUser:
        return CurrentUser(
            user=db.get(User, 1),
            permissions=list(permissions),
            project_id=1,
            system_permissions=list(permissions),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


@pytest.fixture()
def writer(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    client = _make_client(db_session, ["menu:aiqe_runs", "defect:list", "defect:update"])
    yield client
    from app.main import app

    app.dependency_overrides.clear()


@pytest.fixture()
def approver(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    client = _make_client(
        db_session,
        ["menu:aiqe_runs", "defect:list", "defect:update", "aiqe:workflow:approve"],
    )
    yield client
    from app.main import app

    app.dependency_overrides.clear()


def test_create_workflow(writer: TestClient) -> None:
    resp = writer.post("/api/v1/aiqe/workflows", json={"graph": GRAPH})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["version"] == 1
    assert data["approval_status"] == "pending"
    assert len(data["checksum"]) == 64


def test_create_invalid_graph_rejected(writer: TestClient) -> None:
    resp = writer.post(
        "/api/v1/aiqe/workflows", json={"graph": {"schema_version": "1.0", "nodes": []}}
    )
    assert resp.status_code == 400, resp.text


def test_patch_updates_checksum(writer: TestClient) -> None:
    created = writer.post("/api/v1/aiqe/workflows", json={"graph": GRAPH}).json()["data"]
    patched = writer.patch(
        f"/api/v1/aiqe/workflows/{created['id']}", json={"graph": GRAPH_V2}
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["checksum"] != created["checksum"]


def test_approve_requires_dedicated_permission(writer: TestClient) -> None:
    created = writer.post("/api/v1/aiqe/workflows", json={"graph": GRAPH}).json()["data"]
    resp = writer.post(f"/api/v1/aiqe/workflows/{created['id']}/approve")
    assert resp.status_code == 403, resp.text


def test_approve_freezes_and_patch_conflicts(approver: TestClient) -> None:
    created = approver.post("/api/v1/aiqe/workflows", json={"graph": GRAPH}).json()["data"]
    approved = approver.post(f"/api/v1/aiqe/workflows/{created['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["approval_status"] == "approved"
    assert approved.json()["data"]["frozen"] is True

    blocked = approver.patch(
        f"/api/v1/aiqe/workflows/{created['id']}", json={"graph": GRAPH_V2}
    )
    assert blocked.status_code == 409, blocked.text


def test_patch_unknown_workflow_404(approver: TestClient) -> None:
    resp = approver.patch("/api/v1/aiqe/workflows/no-such-workflow", json={"graph": GRAPH})
    assert resp.status_code == 404, resp.text


def test_write_requires_console_menu(db_session: Session) -> None:
    _seed(db_session)
    client = _make_client(db_session, ["defect:update"])
    try:
        resp = client.post("/api/v1/aiqe/workflows", json={"graph": GRAPH})
        assert resp.status_code == 403, resp.text
    finally:
        from app.main import app

        app.dependency_overrides.clear()
