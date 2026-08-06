"""Batch 104 — 自助建项目：自动成员 / 配额 / 所有者权限 / 超管全量。"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.project import Project, ProjectMember
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


@pytest.fixture
def self_service_user(db_session) -> User:
    """普通用户，拥有 project:self_create 与项目业务权限（无全局管理权限）。"""
    perms = [
        ("project:self_create", "自助创建项目", "button"),
        ("testcase:list", "查看用例", "button"),
    ]
    for code, name, ptype in perms:
        db_session.add(Permission(code=code, name=name, type=ptype))
    db_session.flush()
    role = Role(code="tester", name="测试人员", data_scope="project")
    db_session.add(role)
    db_session.flush()
    for p in db_session.query(Permission).filter(Permission.code.in_([c for c, _, _ in perms])):
        db_session.add(RolePermission(role_id=role.id, permission_id=p.id))
    user = User(
        username="alice", password=hash_password("secret123"),
        nickname="Alice", email="alice@t.local", status=1,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id, project_id=0))
    db_session.commit()
    return user


def _login(client, username: str, password: str, project_id: int | None = None) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    headers = {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}
    if project_id:
        headers["X-Project-Id"] = str(project_id)
    return headers


class TestSelfServiceProject:
    def test_create_project_auto_membership(self, client, db_session, self_service_user):
        headers = _login(client, "alice", "secret123")
        resp = client.post("/api/v1/projects", headers=headers, json={
            "code": "MYPROJ",
            "name": "我的项目",
            "description": "自己创建",
        })
        assert resp.status_code == 200
        project_id = resp.json()["data"]["id"]

        member = db_session.query(ProjectMember).filter_by(
            project_id=project_id, user_id=self_service_user.id,
        ).first()
        assert member is not None, "创建者必须自动成为项目成员"
        project = db_session.get(Project, project_id)
        assert project.owner_id == self_service_user.id

        listing = client.get("/api/v1/projects", headers=headers)
        assert listing.status_code == 200
        assert any(item["id"] == project_id for item in listing.json()["data"])

    def test_create_project_quota(self, client, db_session, self_service_user, monkeypatch):
        monkeypatch.setattr(settings, "max_projects_per_user", 1)
        headers = _login(client, "alice", "secret123")
        first = client.post("/api/v1/projects", headers=headers, json={
            "code": "P1", "name": "P1",
        })
        assert first.status_code == 200
        second = client.post("/api/v1/projects", headers=headers, json={
            "code": "P2", "name": "P2",
        })
        assert second.status_code == 400
        assert "上限" in second.json()["msg"]

    def test_owner_can_manage_members(self, client, db_session, self_service_user):
        # 第二个普通用户 bob
        bob = User(
            username="bob", password=hash_password("secret123"),
            nickname="Bob", email="bob@t.local", status=1,
        )
        db_session.add(bob)
        db_session.commit()

        alice_headers = _login(client, "alice", "secret123")
        created = client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "TEAM", "name": "团队项目",
        })
        project_id = created.json()["data"]["id"]

        add = client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=alice_headers,
            json={"user_id": bob.id, "role_id": 0},
        )
        assert add.status_code == 200

        bob_headers = _login(client, "bob", "secret123")
        listing = client.get("/api/v1/projects", headers=bob_headers)
        assert any(item["id"] == project_id for item in listing.json()["data"])

    def test_non_owner_cannot_manage_members(self, client, db_session, self_service_user):
        bob = User(
            username="bob", password=hash_password("secret123"),
            nickname="Bob", email="bob@t.local", status=1,
        )
        db_session.add(bob)
        db_session.commit()

        alice_headers = _login(client, "alice", "secret123")
        created = client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "TEAM", "name": "团队项目",
        })
        project_id = created.json()["data"]["id"]

        bob_headers = _login(client, "bob", "secret123", project_id=project_id)
        add = client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=bob_headers,
            json={"user_id": bob.id, "role_id": 0},
        )
        assert add.status_code == 403

    def test_non_member_cannot_access_project(self, client, db_session, self_service_user):
        bob = User(
            username="bob", password=hash_password("secret123"),
            nickname="Bob", email="bob@t.local", status=1,
        )
        db_session.add(bob)
        db_session.commit()

        alice_headers = _login(client, "alice", "secret123")
        created = client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "PRIV", "name": "私有项目",
        })
        project_id = created.json()["data"]["id"]

        bob_headers = _login(client, "bob", "secret123", project_id=project_id)
        resp = client.get("/api/v1/projects/current", headers=bob_headers)
        assert resp.status_code == 403

    def test_owner_update_delete_allowed(self, client, db_session, self_service_user):
        headers = _login(client, "alice", "secret123")
        created = client.post("/api/v1/projects", headers=headers, json={
            "code": "EDIT", "name": "可编辑",
        })
        project_id = created.json()["data"]["id"]
        update = client.put(
            f"/api/v1/projects/{project_id}", headers=headers,
            json={"name": "改名后"},
        )
        assert update.status_code == 200
        delete = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
        assert delete.status_code == 200
        assert delete.json()["data"]["deleted"] is True

    def test_superadmin_sees_all_projects(self, client, admin_user, db_session, self_service_user):
        alice_headers = _login(client, "alice", "secret123")
        client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "VIS", "name": "可见项目",
        })
        admin_headers = _login(client, "admin_test", "admin123")
        listing = client.get("/api/v1/projects", headers=admin_headers)
        codes = [item["code"] for item in listing.json()["data"]]
        assert "VIS" in codes
        assert "TEST" in codes
