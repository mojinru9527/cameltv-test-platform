"""Batch 172 — B: agent_orchestrator dsh_execution 分发单测。

in-memory SQLite 用 StaticPool（避坑规则）；runner 全部 mock，不触真实凭据/网络。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - 注册全部模型
from app.core.db import Base
from app.models.knowledge import AiArtifact
from app.services.knowledge import agent_orchestrator


@pytest.fixture()
def orch_db(monkeypatch):
    """独立 in-memory DB 会话 + SessionLocal 覆盖。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine)
    monkeypatch.setattr(agent_orchestrator, "SessionLocal", maker)
    # 成功后的自动入库打桩，避免依赖真实 ingest 服务
    monkeypatch.setattr(
        "app.services.knowledge.ingest_service.ingest_agent_task_completed_in_new_session",
        lambda *a, **k: None,
    )
    return maker


@pytest.fixture()
def dsh_ok(monkeypatch):
    monkeypatch.setattr(
        "app.services.dsh.dsh_runner.runtime_available",
        lambda: (True, ""),
    )
    return monkeypatch


def _fake_run(final_response="done", exit_code=0, error=""):
    def fake(task, **kwargs):
        return SimpleNamespace(
            final_response=final_response,
            exit_code=exit_code,
            error=error,
            session_dir="/tmp/sessions",
            timed_out=False,
        )
    return fake


def test_dsh_execution_success(orch_db, dsh_ok, monkeypatch):
    monkeypatch.setattr("app.services.dsh.dsh_runner.run_dsh_task", _fake_run("harness output ok"))
    result = agent_orchestrator.run_agent_in_new_session(
        project_id=1, agent_type="dsh_execution", user_input="run the tests", operator_id=1,
    )
    assert result["status"] == "success"
    assert result["artifact_id"] is not None
    db = orch_db()
    try:
        artifact = db.get(AiArtifact, result["artifact_id"])
        assert artifact is not None
        assert artifact.artifact_type == "dsh_execution"
        assert "harness output ok" in artifact.content_json
    finally:
        db.close()


def test_dsh_execution_failure(orch_db, dsh_ok, monkeypatch):
    monkeypatch.setattr("app.services.dsh.dsh_runner.run_dsh_task", _fake_run(exit_code=1, error="boom"))
    result = agent_orchestrator.run_agent_in_new_session(
        project_id=1, agent_type="dsh_execution", user_input="run the tests", operator_id=1,
    )
    assert result["status"] == "failed"
    assert "boom" in result.get("error", "")


def test_dsh_execution_unavailable(orch_db, monkeypatch):
    monkeypatch.setattr("app.services.dsh.dsh_runner.runtime_available", lambda: (False, "DSH 服务未启用"))
    result = agent_orchestrator.run_agent_in_new_session(
        project_id=1, agent_type="dsh_execution", user_input="run the tests", operator_id=1,
    )
    assert result["status"] == "failed"
    assert "DSH 不可用" in result.get("error", "")


def test_dsh_execution_empty_task(orch_db, dsh_ok, monkeypatch):
    monkeypatch.setattr("app.services.dsh.dsh_runner.run_dsh_task", _fake_run())
    result = agent_orchestrator.run_agent_in_new_session(
        project_id=1, agent_type="dsh_execution", user_input="   ", operator_id=1,
    )
    assert result["status"] == "failed"
    assert "任务文本为空" in result.get("error", "")
