"""Batch 61 forced-password-change server-side guard tests."""
from __future__ import annotations


def _require_password_change(admin_user, db_session) -> None:
    admin_user.must_change_password = True
    db_session.commit()


def test_forced_password_user_cannot_access_business_api(
    client, auth_headers, admin_user, db_session
):
    _require_password_change(admin_user, db_session)

    response = client.get("/api/v1/projects", headers=auth_headers)

    assert response.status_code == 403
    assert response.json()["code"] == 403
    assert "修改密码" in response.json()["msg"]


def test_forced_password_user_cannot_bypass_through_me(
    client, auth_headers, admin_user, db_session
):
    _require_password_change(admin_user, db_session)

    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 403


def test_forced_password_user_can_change_password_and_old_session_expires(
    client, auth_headers, admin_user, db_session
):
    _require_password_change(admin_user, db_session)

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "admin123", "new_password": "Batch61!NewPassword"},
    )

    assert changed.status_code == 200
    db_session.refresh(admin_user)
    assert admin_user.must_change_password is False

    stale_session = client.get("/api/v1/projects", headers=auth_headers)
    assert stale_session.status_code == 401
    assert "会话已失效" in stale_session.json()["msg"]


def test_wrong_old_password_keeps_forced_change_state(
    client, auth_headers, admin_user, db_session
):
    _require_password_change(admin_user, db_session)

    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "wrong-password", "new_password": "Batch61!NewPassword"},
    )

    assert response.status_code == 400
    assert response.json()["msg"] == "原密码错误"
    db_session.refresh(admin_user)
    assert admin_user.must_change_password is True


def test_weak_new_password_is_rejected_without_changing_state(
    client, auth_headers, admin_user, db_session
):
    _require_password_change(admin_user, db_session)

    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"old_password": "admin123", "new_password": "short"},
    )

    assert response.status_code == 422
    db_session.refresh(admin_user)
    assert admin_user.must_change_password is True


def test_password_reset_token_cannot_authenticate_business_api(client, admin_user):
    from app.core.security import create_access_token

    reset_token = create_access_token(admin_user.id, {"type": "password_reset"})
    response = client.get(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {reset_token}",
            "X-Project-Id": "1",
        },
    )

    assert response.status_code == 401
    assert response.json()["msg"] == "令牌类型无效"


def test_legacy_access_token_without_password_version_requires_relogin(client, admin_user):
    from app.core.security import create_access_token

    legacy_token = create_access_token(admin_user.id, {"type": "access"})
    response = client.get(
        "/api/v1/projects",
        headers={
            "Authorization": f"Bearer {legacy_token}",
            "X-Project-Id": "1",
        },
    )

    assert response.status_code == 401
    assert response.json()["msg"] == "会话版本过旧，请重新登录"
