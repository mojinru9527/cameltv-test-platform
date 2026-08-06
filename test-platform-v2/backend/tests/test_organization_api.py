"""Batch 105 — 组织接口测试（个人组织 / 团队组织 / 成员管理 / 配额）。"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


@pytest.fixture
def tester_role(db_session):
    perms = [
        ("testcase:list", "查看用例", "button"),
        ("project:self_create", "自助创建项目", "button"),
    ]
    for code, name, ptype in perms:
        db_session.add(Permission(code=code, name=name, type=ptype))
    db_session.flush()
    role = Role(code="tester", name="测试人员", data_scope="project")
    db_session.add(role)
    db_session.flush()
    for p in db_session.query(Permission).filter(Permission.code.in_([c for c, _, _ in perms])):
        db_session.add(RolePermission(role_id=role.id, permission_id=p.id))
    db_session.commit()
    return role


@pytest.fixture(autouse=True)
def invite_open(monkeypatch):
    """组织接口测试聚焦组织功能，放开注册邀请码要求。"""
    monkeypatch.setattr(settings, "invite_code_required", False)


def _register(client, username: str, email: str) -> dict:
    """通过注册接口创建用户（注册会自动创建个人组织）。"""
    resp = client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": username,
        "email": email,
        "password": "secret123",
        "invite_code": "",
    })
    assert resp.status_code == 200
    # PATTERNS T3：清掉 cookie，后续调用统一走 Authorization 头，避免跨用户串号
    client.cookies.clear()
    return {
        "headers": {"Authorization": f"Bearer {resp.json()['data']['access_token']}"},
        "data": resp.json()["data"],
    }


def _create_user(db_session, username: str, tester_role) -> User:
    user = User(
        username=username, password=hash_password("secret123"),
        nickname=username, email=f"{username}@t.local", status=1,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=tester_role.id, project_id=0))
    db_session.commit()
    return user


class TestOrganizationApi:
    def test_register_creates_personal_organization(self, client, tester_role):
        result = _register(client, "alice", "alice@t.local")
        resp = client.get("/api/v1/organizations", headers=result["headers"])
        assert resp.status_code == 200
        orgs = resp.json()["data"]
        assert len(orgs) == 1
        assert orgs[0]["type"] == "personal"
        assert orgs[0]["my_role"] == 1
        assert orgs[0]["member_count"] == 1

    def test_login_returns_organizations(self, client, tester_role):
        _register(client, "alice", "alice@t.local")
        login = client.post("/api/v1/auth/login", json={
            "username": "alice", "password": "secret123",
        })
        assert login.status_code == 200
        assert len(login.json()["data"]["organizations"]) == 1

    def test_create_team_organization_and_list(self, client, tester_role):
        result = _register(client, "alice", "alice@t.local")
        resp = client.post(
            "/api/v1/organizations",
            headers=result["headers"],
            json={"code": "TEAM1", "name": "测试团队", "description": "demo"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["type"] == "team"
        listing = client.get("/api/v1/organizations", headers=result["headers"])
        types = {item["type"] for item in listing.json()["data"]}
        assert types == {"personal", "team"}

    def test_team_organization_quota(self, client, tester_role, monkeypatch):
        monkeypatch.setattr(settings, "max_team_organizations_per_user", 1)
        result = _register(client, "alice", "alice@t.local")
        first = client.post(
            "/api/v1/organizations", headers=result["headers"],
            json={"code": "T1", "name": "T1"},
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/organizations", headers=result["headers"],
            json={"code": "T2", "name": "T2"},
        )
        assert second.status_code == 400
        assert "上限" in second.json()["msg"]

    def test_owner_manages_members(self, client, db_session, tester_role):
        alice = _register(client, "alice", "alice@t.local")
        bob = _create_user(db_session, "bob", tester_role)
        orgs = client.get("/api/v1/organizations", headers=alice["headers"]).json()["data"]
        personal = next(o for o in orgs if o["type"] == "personal")

        add = client.post(
            f"/api/v1/organizations/{personal['id']}/members",
            headers=alice["headers"],
            json={"user_id": bob.id, "role_id": 3},
        )
        assert add.status_code == 200
        members = client.get(
            f"/api/v1/organizations/{personal['id']}/members", headers=alice["headers"],
        ).json()["data"]
        assert {m["user_id"] for m in members} == {alice["data"]["user"]["id"], bob.id}

        remove = client.delete(
            f"/api/v1/organizations/{personal['id']}/members/{bob.id}",
            headers=alice["headers"],
        )
        assert remove.status_code == 200

    def test_invite_by_username(self, client, db_session, tester_role):
        alice = _register(client, "alice", "alice@t.local")
        bob = _create_user(db_session, "bob", tester_role)
        orgs = client.get("/api/v1/organizations", headers=alice["headers"]).json()["data"]
        personal = next(o for o in orgs if o["type"] == "personal")
        add = client.post(
            f"/api/v1/organizations/{personal['id']}/members",
            headers=alice["headers"],
            json={"username": "bob", "role_id": 3},
        )
        assert add.status_code == 200
        assert add.json()["data"]["user_id"] == bob.id

    def test_invite_unknown_username_rejected(self, client, tester_role):
        alice = _register(client, "alice", "alice@t.local")
        orgs = client.get("/api/v1/organizations", headers=alice["headers"]).json()["data"]
        personal = next(o for o in orgs if o["type"] == "personal")
        add = client.post(
            f"/api/v1/organizations/{personal['id']}/members",
            headers=alice["headers"],
            json={"username": "ghost", "role_id": 3},
        )
        assert add.status_code == 400
        assert "用户不存在" in add.json()["msg"]

    def test_non_owner_cannot_manage_members(self, client, db_session, tester_role):
        alice = _register(client, "alice", "alice@t.local")
        bob_result = _register(client, "bob", "bob@t.local")
        orgs = client.get("/api/v1/organizations", headers=alice["headers"]).json()["data"]
        alice_org = next(o for o in orgs if o["type"] == "personal")

        add = client.post(
            f"/api/v1/organizations/{alice_org['id']}/members",
            headers=bob_result["headers"],
            json={"user_id": bob_result["data"]["user"]["id"], "role_id": 3},
        )
        assert add.status_code == 403

    def test_personal_org_cannot_be_disabled(self, client, tester_role):
        alice = _register(client, "alice", "alice@t.local")
        orgs = client.get("/api/v1/organizations", headers=alice["headers"]).json()["data"]
        personal = next(o for o in orgs if o["type"] == "personal")
        resp = client.delete(
            f"/api/v1/organizations/{personal['id']}", headers=alice["headers"],
        )
        assert resp.status_code == 400

    def test_team_org_update_and_disable_by_owner(self, client, tester_role):
        alice = _register(client, "alice", "alice@t.local")
        created = client.post(
            "/api/v1/organizations", headers=alice["headers"],
            json={"code": "TEAMX", "name": "团队X"},
        ).json()["data"]
        update = client.put(
            f"/api/v1/organizations/{created['id']}",
            headers=alice["headers"],
            json={"name": "团队X改名"},
        )
        assert update.status_code == 200
        disable = client.delete(
            f"/api/v1/organizations/{created['id']}", headers=alice["headers"],
        )
        assert disable.status_code == 200
        assert disable.json()["data"]["disabled"] is True

    def test_org_projects_visible_to_members(self, client, db_session, tester_role):
        alice = _register(client, "alice", "alice@t.local")
        bob = _create_user(db_session, "bob", tester_role)
        created = client.post(
            "/api/v1/projects", headers=alice["headers"],
            json={"code": "ORGP", "name": "组织项目"},
        )
        assert created.status_code == 200
        created = created.json()["data"]
        orgs = client.get("/api/v1/organizations", headers=alice["headers"]).json()["data"]
        personal = next(o for o in orgs if o["type"] == "personal")
        add = client.post(
            f"/api/v1/organizations/{personal['id']}/members",
            headers=alice["headers"],
            json={"user_id": bob.id, "role_id": 3},
        )
        assert add.status_code == 200

        bob_login = client.post("/api/v1/auth/login", json={
            "username": "bob", "password": "secret123",
        }).json()["data"]
        client.cookies.clear()
        bob_headers = {"Authorization": f"Bearer {bob_login['access_token']}"}
        org_projects = client.get(
            f"/api/v1/organizations/{personal['id']}/projects", headers=bob_headers,
        )
        assert org_projects.status_code == 200
        assert any(p["id"] == created["id"] for p in org_projects.json()["data"])
