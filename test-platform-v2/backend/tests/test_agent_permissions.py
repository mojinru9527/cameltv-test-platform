"""Agent 权限拆分测试 —— agent:view (读) vs agent:run (写)。

验证：
- agent:view 可读取执行记录/类型/队列，但不能触发 Agent
- agent:view + agent:run 可读取并可触发/取消
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ═══════════════════════════════════════════════════════
# 自包含夹具 —— 通过依赖覆盖注入不同权限集
# ═══════════════════════════════════════════════════════

@pytest.fixture()
def agent_db():
    """每个测试独立的 in-memory SQLite，含项目 + 成员种子数据."""
    import app.models  # noqa: F401
    from app.core.db import Base
    from app.models.project import Project, ProjectMember
    from app.models.user import User

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    # 种子数据: 测试用户 + 默认项目 + 项目成员关系
    user = User(id=1, username="tester", password="x", nickname="T", email="t@t.local", status=1)
    session.add(user)
    project = Project(id=1, code="test-proj", name="Test Project", owner_id=1, status=1)
    session.add(project)
    member = ProjectMember(project_id=1, user_id=1, role_id=0)
    session.add(member)
    session.commit()

    try:
        yield session
    finally:
        session.close()


def _make_client(db_session, permissions: list[str], project_id: int = 1) -> TestClient:
    """创建 TestClient 并注入指定权限的用户。"""
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User

    def _override_db():
        yield db_session

    def _current_user():
        u = db_session.get(User, 1)
        return CurrentUser(user=u, permissions=permissions, project_id=project_id)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user

    return TestClient(app)


# ═══════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════

READ_ENDPOINTS = [
    ("GET", "/api/v1/agents/runs"),
    ("GET", "/api/v1/agents/runs/1"),
    ("GET", "/api/v1/agents/types"),
    ("GET", "/api/v1/agents/queue"),
    ("GET", "/api/v1/agents/queue/stats"),
]


class TestAgentViewReadOnly:
    """agent:view 用户可读不可写。"""

    def test_read_endpoints_accessible_with_view_permission(self, agent_db):
        """仅 agent:view 可访问所有读端点。"""
        c = _make_client(agent_db, ["agent:view"])
        try:
            for method, url in READ_ENDPOINTS:
                resp = c.get(url, headers={"X-Project-Id": "1"})
                assert resp.status_code == 200, (
                    f"{method} {url} 应返回 200, 实际 {resp.status_code}: {resp.text[:200]}"
                )
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_trigger_forbidden_with_view_only(self, agent_db):
        """仅 agent:view 不能触发 Agent。"""
        c = _make_client(agent_db, ["agent:view"])
        try:
            resp = c.post(
                "/api/v1/agents/run/case_generation",
                headers={"X-Project-Id": "1"},
                json={"query": "生成用例"},
            )
            assert resp.status_code == 403, f"POST trigger 应返回 403, 实际 {resp.status_code}"
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_cancel_forbidden_with_view_only(self, agent_db):
        """仅 agent:view 不能取消队列任务。"""
        c = _make_client(agent_db, ["agent:view"])
        try:
            resp = c.post(
                "/api/v1/agents/queue/1/cancel",
                headers={"X-Project-Id": "1"},
            )
            assert resp.status_code == 403, f"POST cancel 应返回 403, 实际 {resp.status_code}"
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_triggers_check_forbidden_with_view_only(self, agent_db):
        """仅 agent:view 不能触发变更检测。"""
        c = _make_client(agent_db, ["agent:view"])
        try:
            resp = c.post(
                "/api/v1/agents/triggers/check",
                headers={"X-Project-Id": "1"},
                json={"auto_trigger": False},
            )
            assert resp.status_code == 403, f"POST triggers/check 应返回 403, 实际 {resp.status_code}"
        finally:
            from app.main import app
            app.dependency_overrides.clear()


class TestAgentRunWrite:
    """agent:view + agent:run 用户可读可写。"""

    def test_read_endpoints_accessible_with_run_permission(self, agent_db):
        """agent:view + agent:run 可访问所有读端点。"""
        c = _make_client(agent_db, ["agent:view", "agent:run"])
        try:
            for method, url in READ_ENDPOINTS:
                resp = c.get(url, headers={"X-Project-Id": "1"})
                assert resp.status_code == 200, (
                    f"{method} {url} 应返回 200, 实际 {resp.status_code}: {resp.text[:200]}"
                )
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_trigger_succeeds_with_run_permission(self, agent_db):
        """agent:view + agent:run 可触发 Agent（入队成功）。"""
        c = _make_client(agent_db, ["agent:view", "agent:run"])
        try:
            resp = c.post(
                "/api/v1/agents/run/case_generation",
                headers={"X-Project-Id": "1"},
                json={"query": "生成用例"},
            )
            assert resp.status_code == 200, f"POST trigger 应返回 200, 实际 {resp.status_code}: {resp.text[:200]}"
            data = resp.json()
            assert data["code"] == 0
            assert data["data"]["status"] == "pending"
            assert data["data"]["queue_item_id"] > 0
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_cancel_endpoint_accessible_with_run_permission(self, agent_db):
        """agent:view + agent:run 可访问取消端点（不存在的任务返回 404 而非 403）。"""
        c = _make_client(agent_db, ["agent:view", "agent:run"])
        try:
            # 尝试取消一个不存在的队列项 — 应返回 404（权限通过）而非 403（权限拒绝）
            resp = c.post(
                "/api/v1/agents/queue/99999/cancel",
                headers={"X-Project-Id": "1"},
            )
            assert resp.status_code == 200, f"POST cancel 应返回 200, 实际 {resp.status_code}: {resp.text[:200]}"
            assert resp.json()["code"] == 404  # 项不存在，但权限已通过
        finally:
            from app.main import app
            app.dependency_overrides.clear()


class TestNoPermission:
    """无权限用户应被拒绝。"""

    def test_read_denied_without_permission(self, agent_db):
        """无 agent 相关权限 → 读端点返回 403。"""
        c = _make_client(agent_db, [])
        try:
            for method, url in READ_ENDPOINTS:
                resp = c.get(url, headers={"X-Project-Id": "1"})
                assert resp.status_code == 403, f"{method} {url} 应返回 403, 实际 {resp.status_code}"
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_trigger_denied_without_permission(self, agent_db):
        """无 agent 相关权限 → 触发返回 403。"""
        c = _make_client(agent_db, [])
        try:
            resp = c.post(
                "/api/v1/agents/run/case_generation",
                headers={"X-Project-Id": "1"},
                json={"query": "x"},
            )
            assert resp.status_code == 403, f"POST trigger 应返回 403, 实际 {resp.status_code}"
        finally:
            from app.main import app
            app.dependency_overrides.clear()

    def test_cancel_denied_without_permission(self, agent_db):
        """无 agent 相关权限 → 取消返回 403。"""
        c = _make_client(agent_db, [])
        try:
            resp = c.post(
                "/api/v1/agents/queue/1/cancel",
                headers={"X-Project-Id": "1"},
            )
            assert resp.status_code == 403, f"POST cancel 应返回 403, 实际 {resp.status_code}"
        finally:
            from app.main import app
            app.dependency_overrides.clear()
