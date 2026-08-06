"""Batch 104 — 管理员邀请码管理接口测试。"""
from __future__ import annotations

from app.models.invite_code import InviteCode


class TestInviteAdmin:
    def test_admin_create_and_list(self, client, auth_headers):
        resp = client.post("/api/v1/system/invite-codes", headers=auth_headers, json={})
        assert resp.status_code == 200
        code = resp.json()["data"]["code"]
        assert len(code) >= 8

        listing = client.get("/api/v1/system/invite-codes", headers=auth_headers)
        assert listing.status_code == 200
        items = listing.json()["data"]
        assert any(item["code"] == code for item in items)

    def test_admin_disable_then_register_rejected(self, client, db_session, auth_headers):
        resp = client.post("/api/v1/system/invite-codes", headers=auth_headers, json={})
        code = resp.json()["data"]["code"]
        invite_id = resp.json()["data"]["id"]

        disable = client.post(
            f"/api/v1/system/invite-codes/{invite_id}/disable", headers=auth_headers, json={},
        )
        assert disable.status_code == 200
        assert disable.json()["data"]["disabled"] is True

        register = client.post("/api/v1/auth/register", json={
            "username": "newbie",
            "nickname": "新同学",
            "email": "newbie@test.local",
            "password": "secret123",
            "invite_code": code,
        })
        assert register.status_code == 400
        assert "无效" in register.json()["msg"]

    def test_admin_supports_usage_limit_and_expiry(self, client, db_session, auth_headers):
        resp = client.post(
            "/api/v1/system/invite-codes",
            headers=auth_headers,
            json={"usage_limit": 3, "expires_at": "2099-01-01T00:00:00"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["usage_limit"] == 3
        assert data["status"] == 1

    def test_non_admin_forbidden(self, client, db_session):
        # 普通用户（无系统权限）调用邀请码管理 → 403
        from app.core.security import hash_password
        from app.models.rbac import Role, UserRole
        from app.models.user import User
        from app.models.project import Project, ProjectMember

        user = User(
            username="tester_x", password=hash_password("secret123"),
            nickname="Tester", email="t@test.local", status=1,
        )
        db_session.add(user)
        db_session.flush()
        role = Role(code="tester", name="测试人员", data_scope="project")
        db_session.add(role)
        db_session.flush()
        db_session.add(UserRole(user_id=user.id, role_id=role.id, project_id=0))
        project = Project(code="P1", name="P1", owner_id=user.id, status=1)
        db_session.add(project)
        db_session.flush()
        db_session.add(ProjectMember(project_id=project.id, user_id=user.id, role_id=role.id))
        db_session.commit()

        login = client.post("/api/v1/auth/login", json={
            "username": "tester_x", "password": "secret123",
        })
        assert login.status_code == 200
        headers = {
            "Authorization": f"Bearer {login.json()['data']['access_token']}",
            "X-Project-Id": str(project.id),
        }
        resp = client.post("/api/v1/system/invite-codes", headers=headers, json={})
        assert resp.status_code == 403
