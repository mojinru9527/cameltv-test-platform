"""Batch 106 — 组织权限映射：组织负责人/管理员 = 组织内项目管理员。"""
from __future__ import annotations

import pytest

from app.core.security import hash_password
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services import organization_service


@pytest.fixture
def tester_role(db_session):
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
    return role


def _add_user(db_session, username: str, tester_role) -> User:
    user = User(
        username=username, password=hash_password("secret123"),
        nickname=username, email=f"{username}@t.local", status=1,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=tester_role.id, project_id=0))
    db_session.commit()
    return user


def _login(client, username: str, project_id: int | None = None) -> dict:
    resp = client.post("/api/v1/auth/login", json={
        "username": username, "password": "secret123",
    })
    assert resp.status_code == 200
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}
    if project_id:
        headers["X-Project-Id"] = str(project_id)
    return headers


class TestOrgPermissionMapping:
    def test_org_owner_can_manage_org_project(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        bob = _add_user(db_session, "bob", tester_role)
        # alice 建项目（默认个人组织）→ 建团队组织并把项目移过去不现实，改为直接建团队组织再建项目
        team = client.post(
            "/api/v1/organizations", headers=alice_headers,
            json={"code": "TEAMA", "name": "Alice 团队"},
        ).json()["data"]
        project = client.post(
            "/api/v1/projects", headers=alice_headers,
            json={"code": "ORGP1", "name": "组织项目", "organization_id": team["id"]},
        ).json()["data"]

        # 组织负责人直接管理项目成员（无需成为项目负责人）
        add = client.post(
            f"/api/v1/projects/{project['id']}/members",
            headers=alice_headers,
            json={"user_id": bob.id, "role_id": 0},
        )
        assert add.status_code == 200
        gate = client.get(
            f"/api/v1/projects/{project['id']}/quality-gate",
            headers=alice_headers,
        )
        assert gate.status_code == 200

    def test_org_admin_can_manage_org_project(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        bob = _add_user(db_session, "bob", tester_role)
        team = client.post(
            "/api/v1/organizations", headers=alice_headers,
            json={"code": "TEAMB", "name": "Team B"},
        ).json()["data"]
        # bob 提升为组织管理员
        promote = client.post(
            f"/api/v1/organizations/{team['id']}/members",
            headers=alice_headers,
            json={"username": "bob", "role_id": 2},
        )
        assert promote.status_code == 200
        project = client.post(
            "/api/v1/projects", headers=alice_headers,
            json={"code": "ORGP2", "name": "组织项目2", "organization_id": team["id"]},
        ).json()["data"]

        bob_headers = _login(client, "bob", project_id=project["id"])
        members = client.get(
            f"/api/v1/projects/{project['id']}/members", headers=bob_headers,
        )
        assert members.status_code == 200

    def test_org_member_cannot_manage_org_project(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        bob = _add_user(db_session, "bob", tester_role)
        team = client.post(
            "/api/v1/organizations", headers=alice_headers,
            json={"code": "TEAMC", "name": "Team C"},
        ).json()["data"]
        client.post(
            f"/api/v1/organizations/{team['id']}/members",
            headers=alice_headers,
            json={"username": "bob", "role_id": 3},
        )
        project = client.post(
            "/api/v1/projects", headers=alice_headers,
            json={"code": "ORGP3", "name": "组织项目3", "organization_id": team["id"]},
        ).json()["data"]

        bob_headers = _login(client, "bob", project_id=project["id"])
        members = client.get(
            f"/api/v1/projects/{project['id']}/members", headers=bob_headers,
        )
        assert members.status_code == 403

    def test_permission_codes_include_project_manage_for_org_owner(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        team = client.post(
            "/api/v1/organizations", headers=alice_headers,
            json={"code": "TEAMD", "name": "Team D"},
        ).json()["data"]
        project = client.post(
            "/api/v1/projects", headers=alice_headers,
            json={"code": "ORGP4", "name": "组织项目4", "organization_id": team["id"]},
        ).json()["data"]

        login = client.post("/api/v1/auth/login", json={
            "username": "alice", "password": "secret123",
        }).json()["data"]
        client.cookies.clear()
        me = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {login['access_token']}",
                "X-Project-Id": str(project["id"]),
            },
        )
        assert me.status_code == 200
        perms = me.json()["data"]["permissions"]
        assert "project:manage" in perms
        assert "project:update" in perms

    def test_org_owner_manage_requires_org_membership_not_project(self, client, db_session, tester_role):
        """回归：组织负责人在自己的组织项目上操作不需要成为项目负责人/成员。"""
        alice_headers = _login(client, "alice")
        team = client.post(
            "/api/v1/organizations", headers=alice_headers,
            json={"code": "TEAME", "name": "Team E"},
        ).json()["data"]
        project = client.post(
            "/api/v1/projects", headers=alice_headers,
            json={"code": "ORGP5", "name": "组织项目5", "organization_id": team["id"]},
        ).json()["data"]
        # 移除 alice 的项目成员身份（模拟组织维度的访问）
        from app.models.project import ProjectMember
        from sqlalchemy import select
        row = db_session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project["id"],
                ProjectMember.user_id == 1,
            )
        )
        db_session.delete(row)
        db_session.commit()
        gate = client.get(
            f"/api/v1/projects/{project['id']}/quality-gate",
            headers=alice_headers,
        )
        assert gate.status_code == 200
