"""切片 4 —— Wiki API 层：配置读取 + 权限/开关门禁（HTTP）。

主链路(导入→编译→差异→产物)的业务逻辑由 *_in_new_session 后台函数承载，已在
test_wiki_ingest / test_wiki_diff 以组件级(db_session)覆盖；此处只校验 API 接线、
RBAC 与配置开关门禁。
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.project import ProjectMember
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


@pytest.fixture()
def wiki_off(monkeypatch):
    monkeypatch.setattr(settings, "wiki_enabled", False, raising=False)
    monkeypatch.setattr(settings, "wiki_diff_enabled", False, raising=False)


@pytest.fixture()
def wiki_lint_on(monkeypatch):
    monkeypatch.setattr(settings, "wiki_lint_enabled", True, raising=False)


@pytest.fixture()
def wiki_manager_headers(client, db_session):
    """Authenticate a project-scoped wiki manager without super-admin permission."""
    user = User(
        username="wiki_manager",
        password=hash_password("wiki-manager-password"),
        nickname="Wiki Manager",
        email="wiki-manager@test.local",
        status=1,
    )
    permission = Permission(code="wiki:manage", name="Manage Wiki", type="api")
    role = Role(code="wiki_manager", name="Wiki Manager", data_scope="project")
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
        json={"username": user.username, "password": "wiki-manager-password"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Project-Id": "1"}


@pytest.fixture()
def project_wildcard_headers(client, db_session):
    """Authenticate a project-scoped wildcard role that is not a system super-admin."""
    user = User(
        username="project_wildcard",
        password=hash_password("project-wildcard-password"),
        nickname="Project Wildcard",
        email="project-wildcard@test.local",
        status=1,
    )
    permission = Permission(code="*", name="Project Wildcard", type="api")
    role = Role(code="project_wildcard", name="Project Wildcard", data_scope="project")
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
        json={"username": user.username, "password": "project-wildcard-password"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Project-Id": "1"}


def test_config_endpoint(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "wiki_enabled", True, raising=False)
    r = client.get("/api/v1/wiki/config", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["wiki_enabled"] is True and "lanhu_mcp_enabled" in data


def test_import_gated_when_wiki_off(client, auth_headers, wiki_off):
    r = client.post("/api/v1/wiki/import/lanhu", headers=auth_headers,
                    json={"url": "https://lanhuapp.com/x?docId=a&pageId=b"})
    assert r.status_code == 503
    assert "未启用" in r.json()["msg"]


def test_legacy_wiki_lanhu_import_cannot_bypass_evidence_gate(
    client, auth_headers, monkeypatch,
):
    monkeypatch.setattr(settings, "wiki_enabled", True, raising=False)
    response = client.post(
        "/api/v1/wiki/import/lanhu",
        headers=auth_headers,
        json={"url": "https://lanhuapp.com/x?docId=a&pageId=b"},
    )

    assert response.status_code == 409
    assert "证据包质量门禁" in response.json()["msg"]


def test_diff_gated_when_diff_off(client, auth_headers, wiki_off):
    r = client.post("/api/v1/wiki/diff/tasks", headers=auth_headers,
                    json={"query": "比赛推送"})
    assert r.status_code == 503


def test_raw_sources_list_empty(client, auth_headers):
    r = client.get("/api/v1/wiki/raw-sources", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 0


def test_requires_auth(client):
    r = client.get("/api/v1/wiki/config")
    assert r.status_code in (401, 403)


def test_wiki_lint_rejects_cross_project_override_for_non_superuser(
    client, wiki_manager_headers, wiki_lint_on, db_session
):
    """P0: a project wiki manager cannot lint another project via request override."""
    response = client.post(
        "/api/v1/wiki/lint",
        headers=wiki_manager_headers,
        json={"project_id_override": 999},
    )

    assert response.status_code == 403
    assert "super administrator" in response.json()["msg"]
    from app.models.wiki import WikiLintReport
    assert db_session.query(WikiLintReport).count() == 0


def test_wiki_lint_allows_current_project_override_for_non_superuser(
    client, wiki_manager_headers, wiki_lint_on
):
    """P1: explicitly selecting the active project remains valid for a wiki manager."""
    response = client.post(
        "/api/v1/wiki/lint",
        headers=wiki_manager_headers,
        json={"project_id_override": 1},
    )

    assert response.status_code == 200
    assert response.json()["data"]["project_id"] == 1


def test_wiki_lint_allows_cross_project_override_for_superuser(
    client, auth_headers, wiki_lint_on
):
    """P0: a super administrator may deliberately lint another project."""
    response = client.post(
        "/api/v1/wiki/lint",
        headers=auth_headers,
        json={"project_id_override": 999},
    )

    assert response.status_code == 200
    assert response.json()["data"]["project_id"] == 999


def test_wiki_lint_rejects_cross_project_override_for_project_wildcard_role(
    client, project_wildcard_headers, wiki_lint_on, db_session
):
    """P0: project-level '*' permission must not impersonate a system super-admin."""
    response = client.post(
        "/api/v1/wiki/lint",
        headers=project_wildcard_headers,
        json={"project_id_override": 999},
    )

    assert response.status_code == 403
    from app.models.wiki import WikiLintReport
    assert db_session.query(WikiLintReport).count() == 0


def test_permission_codes_exclude_wildcard_role_from_another_project(db_session):
    """P0: role assignments from project 999 never grant permissions in project 1."""
    from app.services import rbac_service

    user = User(
        username="foreign_project_wildcard",
        password=hash_password("unused-password"),
        nickname="Foreign Wildcard",
        email="foreign-wildcard@test.local",
        status=1,
    )
    permission = Permission(code="*", name="Foreign Wildcard", type="api")
    role = Role(code="foreign_project_wildcard", name="Foreign Wildcard", data_scope="project")
    db_session.add_all([user, permission, role])
    db_session.flush()
    db_session.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=999),
    ])
    db_session.commit()

    assert rbac_service.permission_codes(db_session, user.id, project_id=1) == []
    assert rbac_service.permission_codes(db_session, user.id, project_id=999) == ["*"]
