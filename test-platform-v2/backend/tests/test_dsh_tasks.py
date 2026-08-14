"""Batch 172 — C: DSH 任务执行模块 service + API 单测。

in-memory SQLite 用 StaticPool；runner 全部 mock；测试前清 cookie（避坑规则）。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.dsh_task import DshTask
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.services.dsh import dsh_task_service


@pytest.fixture()
def dsh_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine)
    monkeypatch.setattr(dsh_task_service, "SessionLocal", maker)
    # 测试环境不打桩会启动真实后台线程抢任务 → 打桩
    monkeypatch.setattr(dsh_task_service, "ensure_worker_running", lambda: None)
    session = maker()
    user = User(id=1, username="tester", password="x", nickname="T", email="t@t.local", status=1)
    session.add(user)
    project = Project(id=1, code="test-proj", name="Test Project", owner_id=1, status=1)
    session.add(project)
    session.add(ProjectMember(project_id=1, user_id=1, role_id=0))
    session.commit()
    return maker


@pytest.fixture()
def dsh_client(dsh_db):
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User as _User

    def _override_db():
        db = dsh_db()
        try:
            yield db
        finally:
            db.close()

    def _current_user():
        db = dsh_db()
        try:
            u = db.get(_User, 1)
        finally:
            db.close()
        return CurrentUser(user=u, permissions=["agent:view", "agent:run"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def dsh_available(monkeypatch):
    monkeypatch.setattr(
        "app.services.dsh.dsh_runner.runtime_available",
        lambda: (True, ""),
    )
    # router 在模块导入时绑定了 runtime_available 引用，需直接打桩 router 模块
    monkeypatch.setattr(
        "app.api.v1.dsh_tasks.runtime_available",
        lambda: (True, ""),
    )


def _fake_run(final_response="ok", exit_code=0, error=""):
    def fake(task, **kwargs):
        return SimpleNamespace(
            final_response=final_response,
            exit_code=exit_code,
            error=error,
            session_dir="/tmp/dsh-sessions",
            timed_out=False,
        )
    return fake


# ── service ──

def test_submit_and_claim(dsh_db):
    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(db, project_id=1, task="run tests", operator_id=1)
        assert row.status == "pending"
        claimed = dsh_task_service.claim_next_task(db)
        assert claimed is not None and claimed.id == row.id
        assert claimed.status == "running"
        assert claimed.started_at is not None
    finally:
        db.close()


def test_execute_success(dsh_db, monkeypatch):
    monkeypatch.setattr("app.services.dsh.dsh_runner.run_dsh_task", _fake_run("harness result"))
    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(db, project_id=1, task="run tests", operator_id=1)
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed)
        assert claimed.status == "success"
        assert claimed.output_text == "harness result"
        assert claimed.finished_at is not None
    finally:
        db.close()


def test_execute_failure(dsh_db, monkeypatch):
    monkeypatch.setattr("app.services.dsh.dsh_runner.run_dsh_task", _fake_run(exit_code=1, error="boom"))
    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(db, project_id=1, task="run tests", operator_id=1)
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed)
        assert claimed.status == "failed"
        assert "boom" in claimed.error
    finally:
        db.close()


def test_cancel_only_pending(dsh_db):
    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(db, project_id=1, task="run tests", operator_id=1)
        assert dsh_task_service.cancel_task(db, row.id, project_id=1) is not None
        assert row.status == "cancelled"
        # 已取消不可再次取消
        assert dsh_task_service.cancel_task(db, row.id, project_id=1) is None
        # 项目隔离
        assert dsh_task_service.get_task(db, row.id, project_id=999) is None
    finally:
        db.close()


# ── API ──

def test_api_health(dsh_client, dsh_available):
    resp = dsh_client.get("/api/v1/dsh-tasks/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["available"] is True


def test_api_create_list_detail_cancel(dsh_client, dsh_available, monkeypatch):
    monkeypatch.setattr("app.services.dsh.dsh_runner.run_dsh_task", _fake_run("done"))
    r1 = dsh_client.post("/api/v1/dsh-tasks", json={"task": "run the suite"})
    assert r1.status_code == 200
    data = r1.json()["data"]
    task_id = data["id"]
    assert data["status"] == "pending"

    r2 = dsh_client.get("/api/v1/dsh-tasks")
    assert r2.status_code == 200
    assert r2.json()["data"]["total"] >= 1

    r3 = dsh_client.get(f"/api/v1/dsh-tasks/{task_id}")
    assert r3.status_code == 200
    assert r3.json()["data"]["id"] == task_id

    r4 = dsh_client.post(f"/api/v1/dsh-tasks/{task_id}/cancel")
    assert r4.status_code == 200
    assert r4.json()["data"]["status"] == "cancelled"

    # 取消后再次取消 → envelope 404
    r5 = dsh_client.post(f"/api/v1/dsh-tasks/{task_id}/cancel")
    assert r5.status_code == 200
    assert r5.json()["code"] == 404


def test_api_404_other_project(dsh_client, dsh_available):
    resp = dsh_client.get("/api/v1/dsh-tasks/99999")
    assert resp.status_code == 200
    assert resp.json()["code"] == 404


def test_api_create_unavailable(dsh_client, monkeypatch):
    monkeypatch.setattr(
        "app.services.dsh.dsh_runner.runtime_available",
        lambda: (False, "DSH 服务未启用"),
    )
    resp = dsh_client.post("/api/v1/dsh-tasks", json={"task": "run"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 503
