from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.project import Project, ProjectMember
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.release_bundle import ReleaseBundle
from app.models.user import User
from app.models.wiki import WikiRawSource


@pytest.fixture(autouse=True)
def wiki_enabled(monkeypatch):
    monkeypatch.setattr(settings, "wiki_enabled", True, raising=False)


@pytest.fixture()
def wiki_viewer_headers(client, db_session, admin_user):
    user = User(
        username="wiki_viewer",
        password=hash_password("wiki-viewer-password"),
        nickname="Wiki Viewer",
        email="wiki-viewer@test.local",
        status=1,
    )
    permission = Permission(code="wiki:view", name="View Wiki", type="api")
    role = Role(code="wiki_viewer", name="Wiki Viewer", data_scope="project")
    db_session.add_all([user, permission, role])
    db_session.flush()
    db_session.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=1),
        ProjectMember(project_id=1, user_id=user.id, role_id=role.id),
    ])
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "wiki-viewer-password"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Project-Id": "1"}


def test_sync_availability_explains_missing_release_bundle_without_writes(
    client, auth_headers, db_session,
):
    response = client.get("/api/v1/wiki/sync/availability", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is False
    assert "暂无发布包" in data["reason"]
    assert data["release_bundle_id"] is None
    assert db_session.query(WikiRawSource).count() == 0


def test_sync_availability_selects_active_bundle_from_current_project(
    client, auth_headers, db_session,
):
    current = ReleaseBundle(
        project_id=1,
        name="Batch 60 生产验收",
        client_version="60.0.0",
        status="active",
    )
    db_session.add(Project(id=2, code="FOREIGN-WIKI", name="Foreign Wiki"))
    db_session.add_all([
        current,
        ReleaseBundle(
            project_id=2,
            name="其它项目更新版本",
            client_version="99.0.0",
            status="active",
        ),
    ])
    db_session.commit()

    response = client.get("/api/v1/wiki/sync/availability", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "available": True,
        "reason": "",
        "release_bundle_id": current.id,
        "release_bundle_name": current.name,
        "release_bundle_status": "active",
    }


def test_draft_bundle_is_unavailable_and_cannot_be_synced(
    client, auth_headers, db_session,
):
    draft = ReleaseBundle(
        project_id=1,
        name="尚未启用的版本",
        client_version="60.0.0-rc1",
        status="draft",
    )
    db_session.add(draft)
    db_session.commit()

    availability = client.get("/api/v1/wiki/sync/availability", headers=auth_headers)
    sync = client.post(
        f"/api/v1/wiki/sync/bundle/{draft.id}",
        headers=auth_headers,
        json={},
    )

    assert availability.status_code == 200
    assert availability.json()["data"]["available"] is False
    assert "启用" in availability.json()["data"]["reason"]
    assert sync.status_code == 409
    assert db_session.query(WikiRawSource).count() == 0


def test_foreign_bundle_is_not_available_or_syncable(
    client, auth_headers, db_session,
):
    db_session.add(Project(id=2, code="FOREIGN-ONLY", name="Foreign Only"))
    foreign = ReleaseBundle(
        project_id=2,
        name="跨项目发布包",
        client_version="60.0.0",
        status="active",
    )
    db_session.add(foreign)
    db_session.commit()

    availability = client.get("/api/v1/wiki/sync/availability", headers=auth_headers)
    sync = client.post(
        f"/api/v1/wiki/sync/bundle/{foreign.id}",
        headers=auth_headers,
        json={},
    )

    assert availability.status_code == 200
    assert availability.json()["data"]["available"] is False
    assert availability.json()["data"]["release_bundle_id"] is None
    assert sync.status_code == 404
    assert db_session.query(WikiRawSource).count() == 0


def test_view_only_user_can_preflight_but_cannot_trigger_sync(
    client, wiki_viewer_headers, db_session,
):
    bundle = ReleaseBundle(
        project_id=1,
        name="只读用户可见版本",
        client_version="60.0.0",
        status="active",
    )
    db_session.add(bundle)
    db_session.commit()

    availability = client.get(
        "/api/v1/wiki/sync/availability",
        headers=wiki_viewer_headers,
    )
    sync = client.post(
        f"/api/v1/wiki/sync/bundle/{bundle.id}",
        headers=wiki_viewer_headers,
        json={},
    )

    assert availability.status_code == 200
    assert availability.json()["data"]["available"] is True
    assert sync.status_code == 403
    assert db_session.query(WikiRawSource).count() == 0
