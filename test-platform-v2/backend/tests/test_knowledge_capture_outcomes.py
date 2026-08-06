"""Batch 108 — capture 入库结果语义单测。

覆盖：created / disabled / duplicate / error 四类结果 + hooks 失败不翻转成功 +
路由 503/409/500/200 错误映射。
"""

from __future__ import annotations

import pytest

from app.services.knowledge.ingest_service import (
    CaptureIngestResult,
    ingest_capture_in_new_session,
)


@pytest.fixture()
def kdb():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.models  # noqa: F401
    from app.core.db import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    from app.models.project import Project

    session.add(Project(id=1, code="KNOWLEDGE-CAPTURE-TEST", name="Knowledge Capture Test"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def kclient(kdb):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User

    def _override_db():
        yield kdb

    def _super_user():
        u = User(id=1, username="ktester", password="x", nickname="K", email="k@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def ingest_env(monkeypatch, tmp_path):
    """临时 SQLite + monkeypatch SessionLocal/settings，隔离 capture 入库环境。"""
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models import knowledge as km
    from app.services.knowledge import ingest_service
    from app.services.knowledge import chunk_service

    db_path = tmp_path / "capture.db"
    engine = create_engine(f"sqlite:///{db_path}")
    km.Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)

    def _session_local():
        return session_factory()

    monkeypatch.setattr(ingest_service, "SessionLocal", _session_local)
    monkeypatch.setattr(ingest_service.settings, "knowledge_ingest_enabled", True, raising=False)
    # hooks 默认空转，避免依赖外部嵌入/图谱服务
    monkeypatch.setattr(ingest_service, "_post_ingest_hooks", lambda *a, **k: None)
    monkeypatch.setattr(chunk_service, "make_chunks", lambda *a, **k: None)
    return ingest_service


def test_capture_created_then_duplicate(ingest_env) -> None:
    """唯一内容首次入库 created；同标题同内容二次入库 duplicate。"""
    ingest_service = ingest_env
    first = ingest_capture_in_new_session(
        1, title="规范文档", content="唯一正文 unique-capture-1",
        source_url="https://example.com/doc",
    )
    assert first.reason == "created"
    assert first.source_id is not None

    second = ingest_capture_in_new_session(
        1, title="规范文档", content="唯一正文 unique-capture-1",
        source_url="https://example.com/doc",
    )
    assert second.reason == "duplicate"
    assert second.source_id is None


def test_capture_different_content_creates(ingest_env) -> None:
    """不同正文（同标题）应新建而非去重。"""
    a = ingest_capture_in_new_session(1, title="标题", content="正文A unique-x1")
    b = ingest_capture_in_new_session(1, title="标题", content="正文B unique-x2")
    assert a.reason == "created" and b.reason == "created"
    assert a.source_id != b.source_id


def test_capture_disabled_when_toggle_off(ingest_env) -> None:
    """开关关闭 → disabled（不再是 None 混义）。"""
    ingest_service = ingest_env
    ingest_service.settings.knowledge_ingest_enabled = False
    result = ingest_capture_in_new_session(1, title="任意", content="任意内容 unique-x3")
    assert result == CaptureIngestResult("disabled")


def test_capture_error_on_chunk_failure(ingest_env, monkeypatch) -> None:
    """make_chunks 异常 → error。"""
    from app.services.knowledge import chunk_service

    def _boom(*a, **k):
        raise RuntimeError("chunk failed")

    monkeypatch.setattr(chunk_service, "make_chunks", _boom)
    result = ingest_capture_in_new_session(1, title="任意", content="任意内容 unique-x4")
    assert result.reason == "error"


def test_capture_hooks_failure_does_not_flip_created(ingest_env, monkeypatch) -> None:
    """hooks 失败仅记日志，不得把已提交的成功翻转成 error（Batch 108 核心修复）。"""
    ingest_service = ingest_env

    def _hook_boom(*a, **k):
        raise RuntimeError("embedding down")

    monkeypatch.setattr(ingest_service, "_post_ingest_hooks", _hook_boom)
    result = ingest_capture_in_new_session(1, title="任意", content="任意内容 unique-x5")
    assert result.reason == "created"
    assert result.source_id is not None


# ── 路由层错误映射 ──


def test_capture_route_mapping(kclient, kdb, monkeypatch) -> None:
    """路由按 reason 返回 503/409/500/200 且提示明确。"""
    from app.services.knowledge import ingest_service

    outcomes = {
        # (HTTP 状态, 业务码, 响应体提示片段)
        "disabled": (503, 503, "知识入库未启用"),
        "duplicate": (200, 409, "内容重复"),
        "error": (500, 500, "知识入库失败"),
        "created": (200, 0, "captured"),
    }

    def _fake_ingest(_reason: str):
        def _fake(*a, **k):
            return CaptureIngestResult(
                _reason, source_id=42 if _reason == "created" else None
            )
        return _fake

    for reason, (http_status, biz_code, msg_frag) in outcomes.items():
        monkeypatch.setattr(
            ingest_service,
            "ingest_capture_in_new_session",
            _fake_ingest(reason),
        )
        resp = kclient.post(
            "/api/v1/knowledge/capture",
            json={"title": "测试", "content": "内容 unique-route"},
            headers={"X-Project-Id": "1"},
        )
        assert resp.status_code == http_status, f"reason={reason} -> {resp.status_code} {resp.text}"
        body = resp.json()
        assert body.get("code") == biz_code, f"reason={reason} -> {body}"
        assert msg_frag in resp.text
