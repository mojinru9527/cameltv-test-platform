"""Shared test fixtures — in-memory SQLite, test client, seeded data."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.core.security import hash_password
from app.main import app
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory SQLite database per test function."""
    import app.models  # noqa: F401 — ensure all models are registered on Base.metadata
    _ = app.models
    # StaticPool: a single shared connection so the TestClient's request thread
    # and the test thread see the SAME in-memory DB (else → "no such table").
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with DB override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.core.db import get_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session) -> User:
    """Create and return a super-admin user."""
    u = User(
        username="admin_test", password=hash_password("admin123"),
        nickname="Admin", email="admin@test.local", status=1,
    )
    db_session.add(u)
    db_session.flush()

    # Create super-admin role with wildcard permission
    perm = Permission(code="*", name="Super", type="api")
    db_session.add(perm)
    db_session.flush()
    role = Role(code="admin", name="Admin", data_scope="global")
    db_session.add(role)
    db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db_session.add(UserRole(user_id=u.id, role_id=role.id, project_id=0))
    db_session.commit()
    return u


@pytest.fixture(scope="function")
def auth_headers(admin_user, client) -> dict:
    """Login and return Authorization header for the admin user."""
    resp = client.post("/api/v1/auth/login", json={
        "username": "admin_test", "password": "admin123",
    })
    assert resp.status_code == 200
    # LoginOut exposes the JWT as `access_token` (response body still returns it
    # for the transition period alongside the httpOnly cookie).
    token = resp.json()["data"]["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Project-Id": "1",
    }
