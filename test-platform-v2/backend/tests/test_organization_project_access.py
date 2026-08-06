"""Batch 105 — 项目归属组织与组织成员访问控制。"""
from __future__ import annotations

import pytest

from app.core.security import hash_password
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


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


def _login(
    client, username: str, password: str = "secret123", project_id: int | None = None,
) -> dict:
    resp = client.post("/api/v1/auth/login", json={
        "username": username, "password": password,
    })
    assert resp.status_code == 200
    # PATTERNS T3：清掉 cookie，后续调用统一走 Authorization 头，避免跨用户串号
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}
    if project_id:
        headers["X-Project-Id"] = str(project_id)
    return headers


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


class TestOrganizationProjectAccess:
    def test_default_org_is_personal_on_create(self, client, tester_role):
        headers = _login(client, "alice")
        created = client.post("/api/v1/projects", headers=headers, json={
            "code": "DEF", "name": "默认组织项目",
        })
        assert created.status_code == 200
        assert created.json()["data"]["organization_id"] is not None
        listing = client.get("/api/v1/projects", headers=headers)
        assert listing.json()["data"][0]["organization_name"]

    def test_org_member_can_access_org_project(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        bob = _add_user(db_session, "bob", tester_role)
        created = client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "ORG1", "name": "组织项目",
        })
        assert created.status_code == 200
        created = created.json()["data"]
        orgs = client.get("/api/v1/organizations", headers=alice_headers).json()["data"]
        personal = next(o for o in orgs if o["type"] == "personal")
        add = client.post(
            f"/api/v1/organizations/{personal['id']}/members",
            headers=alice_headers,
            json={"user_id": bob.id, "role_id": 3},
        )
        assert add.status_code == 200

        bob_headers = _login(client, "bob", project_id=created["id"])
        current = client.get("/api/v1/projects/current", headers=bob_headers)
        assert current.status_code == 200
        listing = client.get("/api/v1/projects", headers=_login(client, "bob"))
        assert any(p["id"] == created["id"] for p in listing.json()["data"])

    def test_non_org_non_project_member_forbidden(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        carol = _add_user(db_session, "carol", tester_role)
        created = client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "PRIV", "name": "私有项目",
        }).json()["data"]
        carol_headers = _login(client, "carol", project_id=created["id"])
        resp = client.get("/api/v1/projects/current", headers=carol_headers)
        assert resp.status_code == 403

    def test_project_member_outside_org_still_accesses(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        dave = _add_user(db_session, "dave", tester_role)
        created = client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "INV", "name": "邀请项目",
        }).json()["data"]
        # 项目级邀请 dave（不进组织）
        add = client.post(
            f"/api/v1/projects/{created['id']}/members",
            headers=alice_headers,
            json={"user_id": dave.id, "role_id": 0},
        )
        assert add.status_code == 200
        dave_headers = _login(client, "dave", project_id=created["id"])
        current = client.get("/api/v1/projects/current", headers=dave_headers)
        assert current.status_code == 200

    def test_create_in_other_org_forbidden(self, client, db_session, tester_role):
        alice_headers = _login(client, "alice")
        bob = _add_user(db_session, "bob", tester_role)
        # bob 建团队组织
        bob_headers = _login(client, "bob")
        team = client.post(
            "/api/v1/organizations", headers=bob_headers,
            json={"code": "BOBTEAM", "name": "Bob 团队"},
        ).json()["data"]
        # alice 试图往 bob 团队组织里建项目
        resp = client.post(
            "/api/v1/projects", headers=alice_headers,
            json={"code": "X", "name": "X", "organization_id": team["id"]},
        )
        assert resp.status_code == 403

    def test_superadmin_sees_all_org_projects(self, client, admin_user, db_session, tester_role):
        alice_headers = _login(client, "alice")
        client.post("/api/v1/projects", headers=alice_headers, json={
            "code": "VIS2", "name": "可见项目",
        })
        admin_headers = _login(client, "admin_test", password="admin123")
        listing = client.get("/api/v1/projects", headers=admin_headers)
        assert any(p["code"] == "VIS2" for p in listing.json()["data"])
