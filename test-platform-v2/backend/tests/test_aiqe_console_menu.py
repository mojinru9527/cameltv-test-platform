"""batch-336（P1）：执行中心菜单 + `menu:aiqe_runs` RBAC。

覆盖：
1. 种子目录包含执行中心菜单，且 tester 默认分配、viewer 不分配；
2. `/system/menus` 菜单树按权限过滤（有权限出现、无权限消失）；
3. `/api/v1/aiqe/*` 在缺少 `menu:aiqe_runs` 时返回 403，具备权限时可用。
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember
from app.models.rbac import Permission, Role
from app.models.user import User
from app.services.menu_service import menu_tree


def _menu_codes(db: Session, codes: list[str]) -> list[str]:
    return [item.code for item in menu_tree(db, codes)]


def test_seed_catalog_contains_aiqe_runs_menu() -> None:
    from app.seed import _MENUS, _TESTER_MENUS, _VIEWER_MENUS

    paths = {code: path for code, _name, _parent, path, _icon, _sort in _MENUS}
    assert paths["menu:aiqe_runs"] == "/runs", "执行中心菜单必须指向 Run Console 路由"
    assert "menu:aiqe_runs" in _TESTER_MENUS, "tester 默认应可见执行中心"
    assert "menu:aiqe_runs" not in _VIEWER_MENUS, "只读角色不应获得执行中心"


def test_menu_tree_filters_aiqe_runs_by_permission(db_session: Session) -> None:
    db_session.add_all(
        [
            Permission(code="menu:workbench", name="工作台", type="menu", path="/workbench", sort=1),
            Permission(code="menu:aiqe_runs", name="执行中心", type="menu", path="/runs", sort=24),
        ]
    )
    db_session.commit()

    with_perm = _menu_codes(db_session, ["menu:workbench", "menu:aiqe_runs"])
    without_perm = _menu_codes(db_session, ["menu:workbench"])

    assert "menu:aiqe_runs" in with_perm
    assert "menu:aiqe_runs" not in without_perm, "无菜单权限时执行中心不得出现在菜单树"


def _seed_member(db: Session) -> None:
    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    user = User(id=1, username="menu-tester", password="x", nickname="T", email="t@t.local", status=1)
    project = Project(id=1, code="menu-proj", name="Menu Project", owner_id=1, status=1)
    db.add_all([user, project])
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.commit()


def _make_client(db: Session, permissions: list[str]) -> TestClient:
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _override_db() -> Iterator[Session]:
        yield db

    def _current_user() -> CurrentUser:
        user = db.get(User, 1)
        return CurrentUser(
            user=user,
            permissions=list(permissions),
            project_id=1,
            system_permissions=list(permissions),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


@pytest.fixture()
def cleanup_overrides() -> Iterator[None]:
    yield
    from app.main import app

    app.dependency_overrides.clear()


def test_console_api_returns_403_without_menu_permission(
    db_session: Session, cleanup_overrides: None
) -> None:
    _seed_member(db_session)
    client = _make_client(db_session, permissions=["defect:list"])
    resp = client.get("/api/v1/aiqe/admin/profiles")
    assert resp.status_code == 403, resp.text


def test_console_api_allows_with_menu_permission(
    db_session: Session, cleanup_overrides: None
) -> None:
    _seed_member(db_session)
    client = _make_client(db_session, permissions=["menu:aiqe_runs", "defect:list"])
    resp = client.get("/api/v1/aiqe/admin/profiles")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == []


def test_runs_api_returns_403_without_menu_permission(
    db_session: Session, cleanup_overrides: None
) -> None:
    _seed_member(db_session)
    client = _make_client(db_session, permissions=["defect:list"])
    resp = client.get("/api/v1/aiqe/runs")
    assert resp.status_code == 403, resp.text


def test_runs_api_allows_with_menu_permission(
    db_session: Session, cleanup_overrides: None
) -> None:
    _seed_member(db_session)
    client = _make_client(db_session, permissions=["menu:aiqe_runs", "defect:list"])
    resp = client.get("/api/v1/aiqe/runs")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["total"] == 0
