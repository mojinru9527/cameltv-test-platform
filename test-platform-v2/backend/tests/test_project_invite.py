"""Batch 106 — 项目邀请链接：生成/消耗/注册自动入项目与组织。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

import pytest

from app.core.security import hash_password
from app.models.project import ProjectMember
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services import organization_service


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_HEAD = "20260806_merge_batch103_batch105"


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


def _login(client, username: str, password: str = "secret123") -> dict:
    resp = client.post("/api/v1/auth/login", json={
        "username": username, "password": password,
    })
    assert resp.status_code == 200
    client.cookies.clear()
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


def _create_project(client, headers: dict, code: str = "INVAPP") -> dict:
    resp = client.post(
        "/api/v1/projects", headers=headers,
        json={"code": code, "name": "邀请项目"},
    )
    assert resp.status_code == 200
    return resp.json()["data"]


def _register(client, username: str, email: str, project_token: str | None = None) -> dict:
    body = {
        "username": username,
        "nickname": username,
        "email": email,
        "password": "secret123",
        "invite_code": "",
        "project_invite_token": project_token or "",
    }
    resp = client.post("/api/v1/auth/register", json=body)
    client.cookies.clear()
    return resp


def test_migration_creates_project_invite_table(tmp_path: Path) -> None:
    database_path = tmp_path / "batch106.db"
    import sqlalchemy as sa
    engine = sa.create_engine(f"sqlite:///{database_path.as_posix()}")
    metadata = sa.MetaData()
    sa.Table("sys_project", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    metadata.create_all(engine)
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
        "AUTO_CREATE_TABLES": "false",
        "PYTHONPATH": str(BACKEND_ROOT),
    })
    subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", PREVIOUS_HEAD],
        cwd=BACKEND_ROOT, env=env, capture_output=True, check=True, text=True, timeout=60,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT, env=env, capture_output=True, check=True, text=True, timeout=60,
    )
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                sa.text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        assert "sys_project_invite" in tables


class TestProjectInvite:
    def test_owner_generates_invite(self, client, tester_role):
        headers = _login(client, "alice")
        project = _create_project(client, headers)
        resp = client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=headers,
            json={"usage_limit": 3},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["token"]
        assert data["url"].startswith("http")
        assert data["usage_limit"] == 3
        assert data["status"] == 1

    def test_invite_url_uses_configured_frontend_url(
        self, client, tester_role, monkeypatch
    ):
        from app.core.config import settings
        monkeypatch.setattr(
            settings, "frontend_url", "https://cameltv-test-platform1.vercel.app"
        )
        headers = _login(client, "alice")
        project = _create_project(client, headers)
        resp = client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=headers,
            json={},
        )
        assert resp.status_code == 200
        url = resp.json()["data"]["url"]
        assert url.startswith(
            "https://cameltv-test-platform1.vercel.app/register?invite="
        )

    def test_non_owner_cannot_generate(self, client, db_session, tester_role):
        from app.models.project import Project
        alice_headers = _login(client, "alice")
        bob = User(
            username="bob", password=hash_password("secret123"),
            nickname="Bob", email="bob@t.local", status=1,
        )
        db_session.add(bob)
        db_session.flush()
        db_session.add(UserRole(user_id=bob.id, role_id=tester_role.id, project_id=0))
        db_session.commit()
        project = _create_project(client, alice_headers)
        # bob 加入项目（非负责人）
        client.post(
            f"/api/v1/projects/{project['id']}/members",
            headers=alice_headers,
            json={"user_id": bob.id, "role_id": 0},
        )
        bob_headers = _login(client, "bob")
        resp = client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=bob_headers,
            json={},
        )
        assert resp.status_code == 403

    def test_register_with_valid_token_joins_project_and_org(
        self, client, db_session, tester_role
    ):
        alice_headers = _login(client, "alice")
        project = _create_project(client, alice_headers)
        invite = client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=alice_headers,
            json={"usage_limit": 1},
        ).json()["data"]

        resp = _register(client, "newbie", "newbie@t.local", project_token=invite["token"])
        assert resp.status_code == 200

        # 新用户自动成为项目成员
        from sqlalchemy import select
        member = db_session.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project["id"],
                ProjectMember.user_id == 2,
            )
        )
        assert member is not None
        # 自动加入项目所属组织（alice 的个人组织）
        newbie_headers = _login(client, "newbie")
        orgs = client.get("/api/v1/organizations", headers=newbie_headers).json()["data"]
        assert len(orgs) == 2  # 个人组织 + 项目所属组织
        projects = client.get("/api/v1/projects", headers=newbie_headers).json()["data"]
        assert any(p["id"] == project["id"] for p in projects)

    def test_invalid_token_rejected(self, client, tester_role):
        resp = _register(client, "ghost", "ghost@t.local", project_token="bogus-token")
        assert resp.status_code == 400
        assert "无效" in resp.json()["msg"]

    def test_expired_token_rejected(self, client, tester_role):
        alice_headers = _login(client, "alice")
        project = _create_project(client, alice_headers)
        invite = client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=alice_headers,
            json={"expires_at": (
                datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
            ).isoformat()},
        ).json()["data"]
        resp = _register(client, "late", "late@t.local", project_token=invite["token"])
        assert resp.status_code == 400
        assert "过期" in resp.json()["msg"]

    def test_exhausted_token_rejected(self, client, tester_role):
        alice_headers = _login(client, "alice")
        project = _create_project(client, alice_headers)
        invite = client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=alice_headers,
            json={"usage_limit": 1},
        ).json()["data"]
        first = _register(client, "u1", "u1@t.local", project_token=invite["token"])
        assert first.status_code == 200
        second = _register(client, "u2", "u2@t.local", project_token=invite["token"])
        assert second.status_code == 400
        assert "用尽" in second.json()["msg"]

    def test_disable_invite_rejects_registration(self, client, tester_role):
        alice_headers = _login(client, "alice")
        project = _create_project(client, alice_headers)
        invite = client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=alice_headers,
            json={},
        ).json()["data"]
        disable = client.post(
            f"/api/v1/projects/{project['id']}/invites/{invite['id']}/disable",
            headers=alice_headers,
            json={},
        )
        assert disable.status_code == 200
        resp = _register(client, "off", "off@t.local", project_token=invite["token"])
        assert resp.status_code == 400

    def test_list_invites_masked(self, client, tester_role):
        alice_headers = _login(client, "alice")
        project = _create_project(client, alice_headers)
        client.post(
            f"/api/v1/projects/{project['id']}/invites",
            headers=alice_headers,
            json={},
        )
        listing = client.get(
            f"/api/v1/projects/{project['id']}/invites", headers=alice_headers,
        )
        assert listing.status_code == 200
        item = listing.json()["data"][0]
        assert len(item["token"]) > 8
        assert item["status"] == 1
