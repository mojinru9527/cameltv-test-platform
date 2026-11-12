"""batch-337（P1）：Profile / Workflow 审批 API 测试。

覆盖：Workflow 列表/详情/审批/项目隔离/权限门禁；Profile 创建/审批/approved 冻结。
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.aiqe.services.workflow_service import create_workflow
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

GRAPH = {
    "schema_version": "1.0",
    "nodes": [{"id": "n1", "driver": "http"}, {"id": "n2", "driver": "http"}],
    "edges": [{"from": "n1", "to": "n2"}],
}


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="workflow-tester", password="x", nickname="T", email="t@t.local", status=1)
    project = Project(id=1, code="wf-proj", name="WF Project", owner_id=1, status=1)
    other = Project(id=2, code="wf-other", name="Other", owner_id=2, status=1)
    db.add_all([user, project, other])
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
        user = db.get(User, 1)
        return CurrentUser(
            user=user,
            permissions=list(permissions),
            project_id=1,
            system_permissions=list(permissions),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    client = _make_client(db_session, ["menu:aiqe_runs", "defect:list", "defect:update"])
    yield client
    from app.main import app

    app.dependency_overrides.clear()


def _workflow(db: Session, *, project_id: int = 1):
    row = create_workflow(db, project_id=project_id, graph=GRAPH)
    db.commit()
    return row


def test_list_workflows_returns_nodes_and_approval(api: TestClient, db_session: Session) -> None:
    row = _workflow(db_session)
    resp = api.get("/api/v1/aiqe/workflows")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["id"] == row.id
    assert item["node_count"] == 2
    assert item["approval_status"] == "pending"
    assert item["frozen"] is False


def test_workflow_detail_returns_graph(api: TestClient, db_session: Session) -> None:
    row = _workflow(db_session)
    resp = api.get(f"/api/v1/aiqe/workflows/{row.id}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["graph_json"]["nodes"][0]["id"] == "n1"


def test_approve_workflow_freezes_and_is_idempotent(api: TestClient, db_session: Session) -> None:
    row = _workflow(db_session)
    first = api.post(f"/api/v1/aiqe/workflows/{row.id}/approve")
    assert first.status_code == 200, first.text
    body = first.json()["data"]
    assert body["approval_status"] == "approved"
    assert body["frozen"] is True

    second = api.post(f"/api/v1/aiqe/workflows/{row.id}/approve")
    assert second.status_code == 200
    assert second.json()["data"]["approval_status"] == "approved"

    db_session.expire_all()
    fresh = api.get(f"/api/v1/aiqe/workflows/{row.id}").json()["data"]
    assert fresh["approved_by"] == 1
    assert fresh["checksum"] == body["checksum"]


def test_workflow_project_isolation(api: TestClient, db_session: Session) -> None:
    row = _workflow(db_session, project_id=2)
    resp = api.get(f"/api/v1/aiqe/workflows/{row.id}")
    assert resp.status_code == 404, resp.text
    listing = api.get("/api/v1/aiqe/workflows").json()["data"]
    assert listing["total"] == 0


def test_workflows_require_console_permission(db_session: Session) -> None:
    _seed(db_session)
    client = _make_client(db_session, ["defect:list"])
    try:
        assert client.get("/api/v1/aiqe/workflows").status_code == 403
    finally:
        from app.main import app

        app.dependency_overrides.clear()


def test_create_and_approve_profile(api: TestClient) -> None:
    created = api.post(
        "/api/v1/aiqe/admin/profiles",
        json={"name": "本地隔离", "purpose": "core_isolated", "config": {"ns": "iso"}},
    )
    assert created.status_code == 200, created.text
    profile = created.json()["data"]
    assert profile["purpose"] == "core_isolated"
    assert profile["frozen"] is False

    approved = api.post(f"/api/v1/aiqe/admin/profiles/{profile['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["approval_status"] == "approved"
    assert approved.json()["data"]["frozen"] is True

    blocked = api.patch(
        f"/api/v1/aiqe/admin/profiles/{profile['id']}",
        json={"config": {"ns": "changed"}},
    )
    assert blocked.status_code == 409, blocked.text


def test_profile_invalid_purpose_rejected(api: TestClient) -> None:
    resp = api.post(
        "/api/v1/aiqe/admin/profiles",
        json={"name": "bad", "purpose": "unknown", "config": {}},
    )
    assert resp.status_code == 400, resp.text


def test_profile_update_before_approval(api: TestClient) -> None:
    created = api.post(
        "/api/v1/aiqe/admin/profiles",
        json={"name": "可改", "purpose": "integration", "config": {"a": 1}},
    ).json()["data"]
    updated = api.patch(
        f"/api/v1/aiqe/admin/profiles/{created['id']}",
        json={"config": {"a": 2}},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["checksum"] != created["checksum"]
