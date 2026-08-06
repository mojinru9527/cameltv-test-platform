"""Batch 104 — 注册接口测试（邀请码 / 唯一性 / 限流 / 默认角色）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings, settings
from app.core.security import hash_password
from app.models.invite_code import InviteCode
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


@pytest.fixture
def tester_role(db_session):
    """Create a tester role with one business permission for default-role assertion."""
    perm = Permission(code="testcase:list", name="查看用例", type="button")
    db_session.add(perm)
    db_session.flush()
    role = Role(code="tester", name="测试人员", data_scope="project")
    db_session.add(role)
    db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db_session.commit()
    return role


def _add_invite(
    db_session,
    *,
    code: str = "ABC123",
    usage_limit: int = 1,
    used_count: int = 0,
    expires_at: datetime | None = None,
) -> InviteCode:
    inv = InviteCode(
        code=code,
        created_by=0,
        usage_limit=usage_limit,
        used_count=used_count,
        expires_at=expires_at,
        status=1,
    )
    db_session.add(inv)
    db_session.commit()
    return inv


def _register_payload(**overrides) -> dict:
    payload = {
        "username": "alice",
        "nickname": "爱丽丝",
        "email": "alice@test.local",
        "password": "secret123",
        "invite_code": "ABC123",
    }
    payload.update(overrides)
    return payload


class TestRegister:
    def test_register_success_auto_login(self, client, db_session, tester_role):
        _add_invite(db_session)
        resp = client.post("/api/v1/auth/register", json=_register_payload())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["access_token"]
        assert data["user"]["username"] == "alice"
        assert data["projects"] == []
        # httpOnly cookie 已下发，/auth/me 可用
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["data"]["user"]["username"] == "alice"
        # 默认角色生效：tester 的 testcase:list 权限出现在 permissions
        assert "testcase:list" in me.json()["data"]["permissions"]

    def test_register_missing_invite_code(self, client, db_session, tester_role):
        _add_invite(db_session)
        resp = client.post("/api/v1/auth/register", json=_register_payload(invite_code=""))
        assert resp.status_code == 400
        assert "邀请码" in resp.json()["msg"]

    def test_register_invalid_invite_code(self, client, db_session, tester_role):
        _add_invite(db_session)
        resp = client.post("/api/v1/auth/register", json=_register_payload(invite_code="NOPE99"))
        assert resp.status_code == 400
        assert "无效" in resp.json()["msg"]

    def test_register_expired_invite(self, client, db_session, tester_role):
        _add_invite(
            db_session,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        )
        resp = client.post("/api/v1/auth/register", json=_register_payload())
        assert resp.status_code == 400
        assert "过期" in resp.json()["msg"]

    def test_register_exhausted_invite(self, client, db_session, tester_role):
        _add_invite(db_session, usage_limit=1, used_count=1)
        resp = client.post("/api/v1/auth/register", json=_register_payload())
        assert resp.status_code == 400
        assert "用尽" in resp.json()["msg"]

    def test_register_duplicate_username(self, client, db_session, tester_role):
        _add_invite(db_session, usage_limit=2)
        client.post("/api/v1/auth/register", json=_register_payload())
        resp = client.post(
            "/api/v1/auth/register",
            json=_register_payload(username="alice", email="bob@test.local"),
        )
        assert resp.status_code == 400
        assert "用户名" in resp.json()["msg"]

    def test_register_duplicate_email(self, client, db_session, tester_role):
        _add_invite(db_session, usage_limit=2)
        client.post("/api/v1/auth/register", json=_register_payload())
        resp = client.post(
            "/api/v1/auth/register",
            json=_register_payload(username="bob", invite_code="ABC123"),
        )
        assert resp.status_code == 400
        assert "邮箱" in resp.json()["msg"]

    def test_register_disabled(self, client, db_session, tester_role, monkeypatch):
        _add_invite(db_session)
        monkeypatch.setattr(Settings, "effective_registration_enabled", property(lambda self: False))
        resp = client.post("/api/v1/auth/register", json=_register_payload())
        assert resp.status_code == 403
        assert "注册未开放" in resp.json()["msg"]

    def test_register_rate_limited(self, client, db_session, tester_role, monkeypatch):
        _add_invite(db_session)
        from app.core import rate_limit
        monkeypatch.setattr(rate_limit.register_limiter, "is_allowed", lambda key: (False, 60))
        resp = client.post("/api/v1/auth/register", json=_register_payload())
        assert resp.status_code == 429
        assert "频繁" in resp.json()["msg"]

    def test_register_weak_password_rejected(self, client, db_session, tester_role):
        _add_invite(db_session)
        resp = client.post("/api/v1/auth/register", json=_register_payload(password="123"))
        assert resp.status_code == 422
