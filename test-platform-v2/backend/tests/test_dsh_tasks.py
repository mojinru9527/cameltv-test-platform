"""Batch 172 — C: DSH 任务执行模块 service + API 单测。

in-memory SQLite 用 StaticPool；runner 全部 mock；测试前清 cookie（避坑规则）。
Batch 191：+ 团队模式（mode/team_json/batch_mode 校验、execute_task 团队分支轮询）。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
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
from app.services.dsh.dsh_runner import DshRunResult


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
    # 打桩目标必须是 router 模块的引用（dsh_tasks.py `from ... import runtime_available`
    # 是独立绑定）；只打 dsh_runner 模块属性在 DSH 启用环境不生效（R-1 冒烟暴露）。
    monkeypatch.setattr(
        "app.api.v1.dsh_tasks.runtime_available",
        lambda: (False, "DSH 服务未启用"),
    )
    resp = dsh_client.post("/api/v1/dsh-tasks", json={"task": "run"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 503


# ── Batch 191：团队模式 schema / API ──

def test_api_create_team_mode_ok(dsh_client, dsh_available):
    """mode=team + batch_mode=full 创建成功，返回 mode=team 与空 team_json。"""
    resp = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "团队任务", "mode": "team", "params": {"batch_mode": "full"}},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["mode"] == "team"
    assert data["team_json"] == {}
    assert data["status"] == "pending"


def test_api_create_team_light_ok(dsh_client, dsh_available):
    resp = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "轻量团队", "mode": "team", "params": {"batch_mode": "light"}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["mode"] == "team"


def test_api_create_invalid_mode_rejected(dsh_client, dsh_available):
    """非法 mode → 422（Pydantic Literal）。"""
    resp = dsh_client.post("/api/v1/dsh-tasks", json={"task": "x", "mode": "x"})
    assert resp.status_code == 422


def test_api_create_team_missing_batch_mode_rejected(dsh_client, dsh_available):
    """mode=team 缺 params.batch_mode → 422。"""
    resp = dsh_client.post("/api/v1/dsh-tasks", json={"task": "x", "mode": "team"})
    assert resp.status_code == 422
    body = resp.json()
    assert any("batch_mode" in str(d.get("msg", "")) for d in body.get("detail", []))


def test_api_create_team_invalid_batch_mode_rejected(dsh_client, dsh_available):
    """mode=team + batch_mode 非法值 → 422。"""
    resp = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "x", "mode": "team", "params": {"batch_mode": "fullx"}},
    )
    assert resp.status_code == 422


def test_api_create_single_with_batch_mode_rejected(dsh_client, dsh_available):
    """mode=single 带 batch_mode → 422（严格拒绝防误用）。"""
    resp = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "x", "params": {"batch_mode": "full"}},
    )
    assert resp.status_code == 422


def test_api_list_detail_include_mode_and_team_json(dsh_client, dsh_available):
    """列表/详情含 mode 与 team_json（空 = {}）。"""
    r = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "团队任务", "mode": "team", "params": {"batch_mode": "full"}},
    )
    task_id = r.json()["data"]["id"]

    lst = dsh_client.get("/api/v1/dsh-tasks")
    items = lst.json()["data"]["items"]
    found = next(i for i in items if i["id"] == task_id)
    assert found["mode"] == "team"
    assert found["team_json"] == {}

    detail = dsh_client.get(f"/api/v1/dsh-tasks/{task_id}")
    assert detail.json()["data"]["mode"] == "team"
    assert detail.json()["data"]["team_json"] == {}


# ── Batch 191：execute_task 团队分支 ──

def _write_team_json(ws_root: Path, team_id: str, data: dict) -> Path:
    """在隔离工作区写 team.json（插件 TeamState 原文结构）。"""
    team_dir = ws_root / ".agent-teams" / team_id
    team_dir.mkdir(parents=True, exist_ok=True)
    tj = team_dir / "team.json"
    tj.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return tj


def _team_snapshot(team_id: str, name: str = "回归团队", tasks=None) -> dict:
    return {
        "id": team_id,
        "name": name,
        "captainSessionId": f"cap-{team_id}",
        "members": [
            {"id": "m1", "name": "product", "role": "产品", "status": "active"},
            {"id": "m2", "name": "qa", "role": "测试", "status": "active"},
        ],
        "tasks": tasks or [
            {"id": "t1", "subject": "PRD", "status": "completed"},
            {"id": "t2", "subject": "门禁", "status": "in_progress", "dependencies": ["t1"]},
        ],
    }


def test_execute_team_success_polls_and_final_snapshot(dsh_db, monkeypatch, tmp_path):
    """团队分支：轮询 ≥2 次快照写入 team_json，终态快照 + success + output_text。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    ws_root = tmp_path / "ws-isolation"
    ws_root.mkdir()
    team_id = "team-abc"

    poll_writes = []

    def fake_runner(task, **kwargs):
        assert kwargs.get("mode") == "team"
        assert kwargs.get("timeout") == settings.dsh_team_timeout_seconds
        assert kwargs["extra_env"]["DSH_SYSTEM_PROMPT"]  # persona 注入
        # 模拟船长执行：先建队写 v1，稍后更新 v2，最后返回成功
        ws = ws_root / "ws-0001"
        ws.mkdir(exist_ok=True)
        _write_team_json(ws, team_id, _team_snapshot(team_id, "回归团队", tasks=[{"id": "t1", "subject": "PRD", "status": "in_progress"}]))
        time.sleep(0.2)
        _write_team_json(ws, team_id, _team_snapshot(team_id, "回归团队"))
        return DshRunResult(final_response="【最终报告】全部完成", exit_code=0, session_dir=str(tmp_path), workspace=str(ws))

    # 独立短 SessionLocal 计数（R-3：轮询写入路径不引用传入 db）
    orig_session_local = dsh_task_service.SessionLocal

    def counting_session_local(*a, **kw):
        s = orig_session_local(*a, **kw)
        poll_writes.append(s)
        return s

    monkeypatch.setattr(dsh_task_service, "SessionLocal", counting_session_local)

    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "full", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        assert claimed.mode == "team"
        dsh_task_service.execute_task(db, claimed, runner=fake_runner)
        assert claimed.status == "success"
        assert claimed.output_text == "【最终报告】全部完成"
        assert claimed.finished_at is not None
        snap = json.loads(claimed.team_json or "{}")
        assert snap.get("id") == team_id
        assert snap["name"] == "回归团队"
        assert snap["members"][0]["name"] == "product"
        assert len(poll_writes) >= 2, f"轮询写入次数不足: {len(poll_writes)}"
        # R-3：轮询 session 都不是 execute_task 传入的 db
        assert all(s is not db for s in poll_writes)
    finally:
        monkeypatch.setattr(dsh_task_service, "SessionLocal", orig_session_local)
        db.close()


def test_execute_team_failure_keeps_progress(dsh_db, monkeypatch, tmp_path):
    """团队分支失败：status=failed + error 落库，已有 team_json 进度保留（US-4）。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    ws_root = tmp_path / "ws-isolation"
    ws_root.mkdir()
    team_id = "team-fail"

    def fake_runner(task, **kwargs):
        ws = ws_root / "ws-0001"
        ws.mkdir(exist_ok=True)
        _write_team_json(ws, team_id, _team_snapshot(team_id, "失败团队"))
        return DshRunResult(final_response="", exit_code=1, error="profile 不存在", session_dir=str(tmp_path), workspace=str(ws))

    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "full", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed, runner=fake_runner)
        assert claimed.status == "failed"
        assert "profile 不存在" in claimed.error
        snap = json.loads(claimed.team_json or "{}")
        assert snap.get("id") == team_id  # 进度保留
    finally:
        db.close()


def test_execute_team_timeout_marks_failed(dsh_db, monkeypatch, tmp_path):
    """团队超时（runner 返回 124）：failed + error 含超时标识 + team_json 保留。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    ws_root = tmp_path / "ws-isolation"
    ws_root.mkdir()
    team_id = "team-timeout"

    def fake_runner(task, **kwargs):
        ws = ws_root / "ws-0001"
        ws.mkdir(exist_ok=True)
        _write_team_json(ws, team_id, _team_snapshot(team_id, "超时团队"))
        return DshRunResult(final_response="", exit_code=124, timed_out=True, error="dsh 执行超时（>1800s）", session_dir=str(tmp_path), workspace=str(ws))

    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "full", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed, runner=fake_runner)
        assert claimed.status == "failed"
        assert "超时" in claimed.error
        snap = json.loads(claimed.team_json or "{}")
        assert snap.get("id") == team_id
    finally:
        db.close()


def test_execute_team_runner_exception_falls_back(dsh_db, monkeypatch, tmp_path):
    """执行线程异常：failed + 可读 error（R-5 兜底）。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)

    def boom_runner(task, **kwargs):
        raise RuntimeError("runner boom")

    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "full", "workspace": str(tmp_path)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed, runner=boom_runner)
        assert claimed.status == "failed"
        assert "runner boom" in claimed.error
    finally:
        db.close()


def test_team_json_truncate_marker(dsh_db, monkeypatch, tmp_path):
    """team_json 超长截断并加 _truncated 标记。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    monkeypatch.setattr(settings, "dsh_max_output_chars", 200)
    ws_root = tmp_path / "ws-isolation"
    ws_root.mkdir()
    team_id = "team-big"

    def fake_runner(task, **kwargs):
        ws = ws_root / "ws-0001"
        ws.mkdir(exist_ok=True)
        big = _team_snapshot(team_id, "大团队", tasks=[{"id": f"t{i}", "subject": "x" * 50, "status": "pending"} for i in range(30)])
        _write_team_json(ws, team_id, big)
        return DshRunResult(final_response="done", exit_code=0, session_dir=str(tmp_path), workspace=str(ws))

    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "full", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed, runner=fake_runner)
        snap = json.loads(claimed.team_json or "{}")
        assert snap.get("_truncated") is True
        assert len(claimed.team_json) <= settings.dsh_max_output_chars
    finally:
        db.close()


def test_execute_team_heartbeat_prevents_stale_reap(dsh_db, monkeypatch, tmp_path):
    """R-1 冒烟缺陷修复：团队执行期间心跳续期 locked_at，超过 stale 阈值不被回收。

    回归场景：团队任务最长 1800s >> _STALE_CLAIM_SECONDS(300s)，无心跳会被
    reap_stale 误回收置 failed（Batch 191 R-1 真实冒烟暴露）。
    """
    import threading as _threading

    from app.core.config import settings
    from app.core.task_queue import reap_stale

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    monkeypatch.setattr(settings, "dsh_team_heartbeat_seconds", 0.05)

    release = _threading.Event()
    calls = []

    def fake_runner(task, **kwargs):
        calls.append(kwargs.get("mode"))
        release.wait(5)  # 阻塞模拟长执行（真实场景 30 分钟级）
        return DshRunResult(final_response="ok", exit_code=0, session_dir=str(tmp_path), workspace="")

    db = dsh_db()
    try:
        dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "light"},
        )
        claimed = dsh_task_service.claim_next_task(db)
        assert claimed is not None and claimed.status == "running"

        # execute_task 会 join 到 runner 释放，放线程执行
        t = _threading.Thread(
            target=dsh_task_service.execute_task,
            args=(db, claimed),
            kwargs={"runner": fake_runner},
            daemon=True,
        )
        t.start()
        time.sleep(0.3)  # > stale 阈值(0.1s)，期间心跳应持续续期 locked_at
        reaped = reap_stale(db, dsh_task_service._DSH_QUEUE, stale_seconds=0.1)
        assert reaped == 0, f"团队执行中不应被 stale 回收: reaped={reaped}"
        release.set()
        t.join(10)
        assert not t.is_alive(), "execute_task 线程未在预期时间内结束"
        assert claimed.status == "success", f"status={claimed.status} error={claimed.error}"
        assert calls == ["team"]
    finally:
        release.set()
        db.close()


def test_execute_team_final_snapshot_reads_archived_team(dsh_db, monkeypatch, tmp_path):
    """Batch 191 冒烟修复：船长删除团队（归档 archive/<teamId>/team.json）后，
    轮询与终态读取仍能读到快照（glob 递归覆盖 archive 路径，任务 10 实测回归）。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    ws_root = tmp_path / "ws-isolation-arch"
    ws_root.mkdir()

    def fake_runner(task, **kwargs):
        ws = ws_root / "ws-0001"
        # 模拟船长删除团队：team.json 落在 .agent-teams/archive/<teamId>/ 下
        team_dir = ws / ".agent-teams" / "archive" / "team-archived"
        team_dir.mkdir(parents=True, exist_ok=True)
        tj = team_dir / "team.json"
        tj.write_text(json.dumps(_team_snapshot("team-archived", "已归档团队"), ensure_ascii=False), encoding="utf-8")
        return DshRunResult(final_response="done", exit_code=0, session_dir=str(tmp_path), workspace=str(ws))

    db = dsh_db()
    try:
        dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "light", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed, runner=fake_runner)
        assert claimed.status == "success"
        snap = json.loads(claimed.team_json or "{}")
        assert snap.get("id") == "team-archived", f"归档团队快照未读到: {snap.get('id')}"
        assert snap.get("name") == "已归档团队"
    finally:
        db.close()


def test_execute_team_poller_follows_latest_team(dsh_db, monkeypatch, tmp_path):
    """Batch 191 冒烟修复：船长同任务重建团队（旧团队被废弃）时，
    轮询/终态跟随 mtime 最新的团队，而非永久锁定首个命中团队（任务 10 实测回归）。"""
    import threading as _threading

    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    ws_root = tmp_path / "ws-isolation-multi"
    ws_root.mkdir()
    release = _threading.Event()

    def fake_runner(task, **kwargs):
        ws = ws_root / "ws-0001"
        # 先建旧团队（active 路径），稍后船长重建新团队（归档路径，mtime 更新）
        _write_team_json(ws, "team-old", _team_snapshot("team-old", "旧团队"))
        release.wait(5)
        team_dir = ws / ".agent-teams" / "archive" / "team-new"
        team_dir.mkdir(parents=True, exist_ok=True)
        tj = team_dir / "team.json"
        tj.write_text(json.dumps(_team_snapshot("team-new", "新团队"), ensure_ascii=False), encoding="utf-8")
        time.sleep(0.1)  # 保证 mtime 递增（Windows 文件时间粒度）
        return DshRunResult(final_response="done", exit_code=0, session_dir=str(tmp_path), workspace=str(ws))

    db = dsh_db()
    try:
        dsh_task_service.submit_task(
            db, project_id=1, task="团队任务", operator_id=1,
            mode="team", params={"batch_mode": "light", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        # execute_task 会 join 到 runner 释放，放线程执行；释放前轮询应已锁定旧团队
        t = _threading.Thread(target=dsh_task_service.execute_task, args=(db, claimed), kwargs={"runner": fake_runner}, daemon=True)
        t.start()
        time.sleep(0.3)  # 轮询数轮（旧团队已被写入快照）
        release.set()
        t.join(15)
        assert claimed.status == "success"
        snap = json.loads(claimed.team_json or "{}")
        assert snap.get("id") == "team-new", f"快照未跟随最新团队: {snap.get('id')}"
    finally:
        release.set()
        db.close()


# ── DSH 测试 Agent 框架：team_kind 分派 ──

def test_execute_team_team_kind_tester_uses_tester_persona(dsh_db, monkeypatch, tmp_path):
    """params.team_kind=tester → DSH_SYSTEM_PROMPT 注入 tester_team_persona（测试视角）。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    ws_root = tmp_path / "ws-isolation"
    ws_root.mkdir()
    team_id = "team-tester"
    injected = {}

    def fake_runner(task, **kwargs):
        injected["prompt"] = kwargs["extra_env"]["DSH_SYSTEM_PROMPT"]
        assert kwargs.get("mode") == "team"
        ws = ws_root / "ws-0001"
        ws.mkdir(exist_ok=True)
        _write_team_json(ws, team_id, _team_snapshot(team_id, "测试团队"))
        return DshRunResult(final_response="【最终报告】测试完成", exit_code=0, session_dir=str(tmp_path), workspace=str(ws))

    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(
            db, project_id=1, task="为登录模块设计用例并执行", operator_id=1,
            mode="team", params={"batch_mode": "full", "team_kind": "tester", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed, runner=fake_runner)
        assert claimed.status == "success"
        prompt = injected["prompt"]
        assert "tester-lead" in prompt
        assert "analyst" in prompt and "case-designer" in prompt and "reviewer" in prompt
        assert "test-case-design skill" in prompt
        assert "trigger_test_execution" in prompt
        # 开发批次专属成员不得混入
        assert "product" not in prompt
    finally:
        db.close()


def test_execute_team_team_kind_dev_uses_dev_persona(dsh_db, monkeypatch, tmp_path):
    """缺省/显式 team_kind=dev → 沿用 agent_team_persona（开发批次不回归）。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "dsh_team_poll_seconds", 0.05)
    ws_root = tmp_path / "ws-isolation"
    ws_root.mkdir()
    team_id = "team-dev"
    injected = {}

    def fake_runner(task, **kwargs):
        injected["prompt"] = kwargs["extra_env"]["DSH_SYSTEM_PROMPT"]
        ws = ws_root / "ws-0001"
        ws.mkdir(exist_ok=True)
        _write_team_json(ws, team_id, _team_snapshot(team_id, "开发团队"))
        return DshRunResult(final_response="done", exit_code=0, session_dir=str(tmp_path), workspace=str(ws))

    db = dsh_db()
    try:
        row = dsh_task_service.submit_task(
            db, project_id=1, task="开发批次任务", operator_id=1,
            mode="team", params={"batch_mode": "full", "team_kind": "dev", "workspace": str(ws_root)},
        )
        claimed = dsh_task_service.claim_next_task(db)
        dsh_task_service.execute_task(db, claimed, runner=fake_runner)
        assert claimed.status == "success"
        prompt = injected["prompt"]
        assert "product" in prompt and "dev" in prompt and "qa" in prompt
        assert "tester-lead" not in prompt
    finally:
        db.close()


def test_api_create_team_tester_kind_ok(dsh_client, dsh_available):
    """mode=team + team_kind=tester 创建成功（batch_mode 必填规则不变）。"""
    resp = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "测试任务", "mode": "team", "params": {"batch_mode": "full", "team_kind": "tester"}},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["mode"] == "team"
    assert data["status"] == "pending"


def test_api_create_team_invalid_team_kind_rejected(dsh_client, dsh_available):
    """mode=team + team_kind 非法值 → 422。"""
    resp = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "x", "mode": "team", "params": {"batch_mode": "full", "team_kind": "hacker"}},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert any("team_kind" in str(d.get("msg", "")) for d in body.get("detail", []))


def test_api_create_single_with_team_kind_rejected(dsh_client, dsh_available):
    """mode=single 带 team_kind → 422（严格拒绝防误用）。"""
    resp = dsh_client.post(
        "/api/v1/dsh-tasks",
        json={"task": "x", "params": {"team_kind": "tester"}},
    )
    assert resp.status_code == 422
