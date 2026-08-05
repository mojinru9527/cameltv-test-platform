"""C31-3 — 运营只读（viewer）角色测试：可查看、不可写。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.models.rbac import Permission, Role, RolePermission
from app.models.project import Project, ProjectMember
from app.models.user import User


@pytest.fixture()
def viewer_db():
    import app.models  # noqa: F401

    from app.seed import _VIEWER_ACTIONS, _VIEWER_MENUS

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    user = User(id=1, username="viewer", password="x", nickname="运营只读",
                email="viewer@local", status=1)
    session.add(user)
    session.add(Project(id=1, code="proj", name="P", owner_id=1, status=1))
    role = Role(code="viewer", name="运营只读", data_scope="project")
    session.add(role)
    session.flush()
    for code in sorted(_VIEWER_MENUS | _VIEWER_ACTIONS):
        perm = Permission(code=code, name=code, type="button")
        session.add(perm)
        session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    session.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _make_client(db_session):
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.services import rbac_service

    def _override_db():
        yield db_session

    def _current_user():
        u = db_session.get(User, 1)
        return CurrentUser(
            user=u,
            permissions=rbac_service.permission_codes(db_session, 1, 1),
            project_id=1,
            system_permissions=rbac_service.permission_codes(db_session, 1),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


def test_viewer_can_list_but_not_create_cases(viewer_db):
    c = _make_client(viewer_db)
    try:
        resp_list = c.get("/api/v1/test-cases", headers={"X-Project-Id": "1"})
        assert resp_list.status_code == 200, resp_list.text

        resp_create = c.post(
            "/api/v1/test-cases",
            headers={"X-Project-Id": "1"},
            json={"title": "viewer 不应能建"},
        )
        assert resp_create.status_code == 403, resp_create.text
    finally:
        from app.main import app
        app.dependency_overrides.clear()


def test_viewer_cannot_create_defect(viewer_db):
    c = _make_client(viewer_db)
    try:
        resp = c.post(
            "/api/v1/defects",
            headers={"X-Project-Id": "1"},
            json={"title": "viewer 不应能建缺陷"},
        )
        assert resp.status_code == 403, resp.text
    finally:
        from app.main import app
        app.dependency_overrides.clear()


def test_viewer_can_view_report_and_defect_list(viewer_db):
    c = _make_client(viewer_db)
    try:
        assert c.get("/api/v1/reports", headers={"X-Project-Id": "1"}).status_code == 200
        assert c.get("/api/v1/defects", headers={"X-Project-Id": "1"}).status_code == 200
    finally:
        from app.main import app
        app.dependency_overrides.clear()
