"""AI 配置 API 测试：权限 + CRUD 闭环。

fixture 对齐 tests/test_dsh_tasks.py 的 dependency_overrides 模式：
in-memory SQLite（StaticPool）+ Base.metadata.create_all（顶部 import app.models），
override get_db / get_current_user，不走真实登录，无需 X-Project-Id header。
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  # 注册全部模型，保证 create_all 建全表
from app.core.db import Base
from app.models.project import Project, ProjectMember
from app.models.user import User


@pytest.fixture()
def ai_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine)

    session = maker()
    user = User(id=1, username="tester", password="x", nickname="T", email="t@t.local", status=1)
    session.add(user)
    project = Project(id=1, code="test-proj", name="Test Project", owner_id=1, status=1)
    session.add(project)
    session.add(ProjectMember(project_id=1, user_id=1, role_id=0))
    session.commit()
    return maker


@contextmanager
def _granted_client(ai_db, permissions):
    """按 permissions 构造一个已登录用户上下文（override get_current_user）。"""
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    def _override_db():
        db = ai_db()
        try:
            yield db
        finally:
            db.close()

    def _current_user():
        db = ai_db()
        try:
            u = db.get(User, 1)
        finally:
            db.close()
        return CurrentUser(user=u, permissions=permissions, project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def client(ai_db):
    """默认拥有 view + manage 全权限的 client（CRUD 闭环用）。"""
    with _granted_client(ai_db, ["ai_config:view", "ai_config:manage"]) as c:
        yield c


def test_list_providers_empty(client):
    resp = client.get("/api/v1/ai-config/providers")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_create_and_list_masks_key(client):
    resp = client.post("/api/v1/ai-config/providers", json={
        "name": "DeepSeek 官方", "provider_type": "openai_compatible",
        "api_base_url": "https://api.deepseek.com", "api_key": "sk-test-1234567890abcdef",
        "models": ["deepseek-v4-pro"], "default_model": "deepseek-v4-pro", "is_default": True,
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] >= 1
    lst = client.get("/api/v1/ai-config/providers").json()["data"]
    assert lst[0]["api_key"] == "sk****cdef"  # 掩码，不出明文
    assert "api_key_encrypted" not in lst[0]


def test_resolve_configured(client):
    client.post("/api/v1/ai-config/providers", json={
        "name": "DeepSeek 官方", "api_key": "sk-test-abc", "models": ["deepseek-v4-pro"],
        "default_model": "deepseek-v4-pro", "is_default": True,
    })
    resolved = client.get("/api/v1/ai-config/resolve").json()["data"]
    assert resolved["configured"] is True
    assert resolved["provider"]["name"] == "DeepSeek 官方"


def test_resolve_unconfigured(client):
    resolved = client.get("/api/v1/ai-config/resolve").json()["data"]
    assert resolved["configured"] is False
    assert resolved["provider"] is None


def test_delete_default_forbidden(client):
    pid = client.post("/api/v1/ai-config/providers", json={
        "name": "A", "api_key": "k", "models": ["m"], "is_default": True,
    }).json()["data"]["id"]
    resp = client.delete(f"/api/v1/ai-config/providers/{pid}")
    assert resp.status_code == 400  # 默认提供方不可删除


def test_create_requires_model(client):
    resp = client.post("/api/v1/ai-config/providers", json={"name": "A", "models": []})
    assert resp.status_code == 400
    assert resp.json()["code"] == 400


def test_permission_denied(ai_db):
    """permissions=[] 的 client：view/manage 均被 403 拒绝。"""
    with _granted_client(ai_db, []) as c:
        assert c.get("/api/v1/ai-config/providers").status_code == 403
        assert c.get("/api/v1/ai-config/resolve").status_code == 403
        assert c.post("/api/v1/ai-config/providers", json={"name": "A", "models": ["m"]}).status_code == 403
