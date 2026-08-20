# C87-3 项目级角色权限测试（B87-Q1 回归）
# 契约：
# - tester 矩阵必须包含项目内日常业务权限（testcase:create 等）
# - tester 矩阵不得包含系统/项目管理/生产操作权限
# - 项目内 tester 成员建用例 200；跨项目 403；建系统用户 403
# 根因：seed.py `_TESTER_ACTIONS` 缺失 tester 核心业务权限。
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

# tester 矩阵契约（与 Design Spec §1.2 对齐）
REQUIRED_TESTER_CODES = {
    "testcase:list", "testcase:detail", "testcase:create", "testcase:update",
    "testcase:delete", "testcase:export",
    "testplan:list", "testplan:detail", "testplan:create", "testplan:update",
    "testplan:delete", "testplan:execute",
    "report:list", "report:detail", "report:create",
    "schedule:create", "schedule:update", "schedule:delete", "schedule:trigger",
    "defect:list", "defect:detail", "defect:create", "defect:update",
    "requirement:upload", "requirement:generate", "requirement:import",
    "dataset:list", "dataset:create", "dataset:update", "dataset:delete",
    "review:submit", "review:approve",
    "mission:list", "mission:detail", "mission:create", "mission:update",
    "mission:log",
    "notify:list", "notify:manage",
    "uitest:list", "uitest:detail", "uitest:create", "uitest:update",
    "uitest:delete", "uitest:trigger",
}

# 明确不授予 tester 的管理/生产/系统权限
FORBIDDEN_TESTER_CODES = {
    "system:user:create", "system:user:update", "system:user:delete",
    "system:role:create", "system:role:update", "system:role:delete",
    "system:audit:list",
    "project:create", "project:update", "project:delete", "project:manage",
    "token:manage",
    "knowledge:manage", "knowledge:approve",
    "wiki:manage", "wiki:approve",
    "agent:run", "agent:admin",
    "ai_artifact:import",
    "lanhu_evidence:import", "lanhu_evidence:review",
    "integration:sync_prod", "apitest:execute_prod", "uitest:trigger_prod",
    "report:delete", "defect:delete", "mission:delete", "mission:generate",
    "release:view",
}


def _seed_tester_rbac(db):
    """按 seed 目录常量建 tester 角色 + 权限关联（真实聚合路径）。"""
    from app.seed import _TESTER_ACTIONS, _TESTER_MENUS

    role = Role(code="tester", name="测试人员", data_scope="project")
    db.add(role)
    db.flush()
    for code in sorted(_TESTER_MENUS | _TESTER_ACTIONS):
        perm = Permission(code=code, name=code, type="button")
        db.add(perm)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    return role


@pytest.fixture()
def rbac_db():
    """独立 in-memory SQLite：tester 用户 + 项目 1 成员（tester 角色）。"""
    import app.models  # noqa: F401 — 注册全部模型

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    user = User(id=1, username="tester", password="x", nickname="T",
                email="t@t.local", status=1)
    session.add(user)
    proj1 = Project(id=1, code="proj-a", name="Project A", owner_id=1, status=1)
    proj2 = Project(id=2, code="proj-b", name="Project B", owner_id=2, status=1)
    session.add_all([proj1, proj2])
    role = _seed_tester_rbac(session)
    session.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _make_client(db_session, user_id: int, project_id: int) -> TestClient:
    """TestClient + 真实 rbac_service 聚合出的权限。"""
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.services import rbac_service

    def _override_db():
        yield db_session

    def _current_user():
        u = db_session.get(User, user_id)
        return CurrentUser(
            user=u,
            permissions=rbac_service.permission_codes(db_session, user_id, project_id),
            project_id=project_id,
            system_permissions=rbac_service.permission_codes(db_session, user_id),
        )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


class TestTesterMatrix:
    def test_matrix_contains_core_business_codes(self):
        """tester 矩阵必须包含项目内日常业务权限（B87-Q1 核心）。"""
        from app.seed import _TESTER_ACTIONS

        missing = REQUIRED_TESTER_CODES - set(_TESTER_ACTIONS)
        assert not missing, f"tester 矩阵缺失: {sorted(missing)}"

    def test_matrix_excludes_management_and_production_codes(self):
        """tester 矩阵不得包含系统/项目管理/生产操作权限。"""
        from app.seed import _TESTER_ACTIONS

        overlap = set(_TESTER_ACTIONS) & FORBIDDEN_TESTER_CODES
        assert not overlap, f"tester 矩阵误含: {sorted(overlap)}"


class TestProjectLevelBehavior:
    def test_tester_can_create_case_in_own_project(self, rbac_db):
        """项目内 tester 成员建用例应 200（修复前 403）。"""
        c = _make_client(rbac_db, 1, 1)
        try:
            resp = c.post(
                "/api/v1/test-cases",
                headers={"X-Project-Id": "1"},
                json={"title": "tester 建用例（C87-3）"},
            )
            assert resp.status_code == 200, (
                f"期望 200，实际 {resp.status_code}: {resp.text[:300]}"
            )
            body = resp.json()
            assert body["code"] == 0
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_tester_cannot_create_system_user(self, rbac_db):
        """tester 不得拥有 system:user:create。"""
        c = _make_client(rbac_db, 1, 1)
        try:
            resp = c.post(
                "/api/v1/system/users",
                headers={"X-Project-Id": "1"},
                json={"username": "x", "password": "x", "nickname": "x"},
            )
            assert resp.status_code == 403, (
                f"期望 403，实际 {resp.status_code}: {resp.text[:300]}"
            )
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_cross_project_still_forbidden(self, rbac_db):
        """tester 不是项目 2 成员 → 访问项目 2 资源仍 403（隔离不放宽）。"""
        c = _make_client(rbac_db, 1, 2)
        try:
            resp = c.post(
                "/api/v1/test-cases",
                headers={"X-Project-Id": "2"},
                json={"title": "cross project"},
            )
            assert resp.status_code == 403, (
                f"期望 403，实际 {resp.status_code}: {resp.text[:300]}"
            )
        finally:
            from app.main import app
            app.dependency_overrides.clear()
