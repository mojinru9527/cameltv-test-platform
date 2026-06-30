"""Auth module tests — login, token validation, RBAC."""
from __future__ import annotations

from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.models.user import User


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "my-secret-password"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)
        assert not verify_password("wrong-password", hashed)

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed)

    def test_long_password(self):
        """bcrypt truncates at 72 bytes — verify this works."""
        long_pw = "a" * 100
        hashed = hash_password(long_pw)
        assert verify_password(long_pw, hashed)


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("42")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        assert decode_token("invalid.token.here") is None

    def test_decode_empty(self):
        assert decode_token("") is None


class TestLoginAPI:
    def test_login_success(self, client, admin_user):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin_test", "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert data["user"]["username"] == "admin_test"

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin_test", "password": "wrong",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "username": "noone", "password": "nopass",
        })
        assert resp.status_code == 401

    def test_me_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "admin_test"

    def test_me_no_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_disabled_user_cannot_login(self, client, db_session):
        u = db_session.query(User).filter_by(username="admin_test").first()
        u.status = 0
        db_session.commit()
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin_test", "password": "admin123",
        })
        assert resp.status_code == 401
