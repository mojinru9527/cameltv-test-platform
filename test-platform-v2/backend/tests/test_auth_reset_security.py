"""Security tests for password reset token expiry and replay resistance."""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.security import create_access_token, decode_token, password_token_version


def test_password_reset_token_honors_explicit_expiry():
    token = create_access_token(
        1,
        {"type": "password_reset", "pwdv": "version"},
        expires_minutes=30,
    )
    payload = decode_token(token)
    assert payload is not None
    lifetime = datetime.fromtimestamp(payload["exp"], timezone.utc) - datetime.now(timezone.utc)
    assert 29 <= lifetime.total_seconds() / 60 <= 31


def test_password_reset_token_can_only_be_consumed_once(client, admin_user):
    token = create_access_token(
        admin_user.id,
        {
            "type": "password_reset",
            "pwdv": password_token_version(admin_user.password),
            "jti": "test-jti",
        },
        expires_minutes=30,
    )

    first = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "new-password-123"},
    )
    assert first.status_code == 200
    assert first.json()["code"] == 0

    second = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "another-password-456"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["code"] == 400
    assert "已使用" in second.json()["msg"]
