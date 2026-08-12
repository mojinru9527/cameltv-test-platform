"""Batch 164 / C163-1 — 调度运行 stale 回收 / heartbeat 回归测试。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.test_schedule import TestScheduleRun as _TestScheduleRun
from app.core.scheduler import reap_stale_schedule_runs as _reap


def _create_manual_schedule(client, auth_headers):
    case = client.post("/api/v1/test-cases", json={"title": "B164TMP-用例", "case_type": "manual"}, headers=auth_headers)
    assert case.status_code == 200, case.text
    plan = client.post("/api/v1/test-plans", json={"name": "B164TMP-计划"}, headers=auth_headers)
    assert plan.status_code == 200, plan.text
    add = client.post(f"/api/v1/test-plans/{plan.json()['data']['id']}/cases",
                      json={"case_ids": [case.json()["data"]["id"]]}, headers=auth_headers)
    assert add.status_code == 200, add.text
    sch = client.post("/api/v1/schedules", json={
        "name": "B164TMP-调度", "plan_id": plan.json()["data"]["id"], "job_type": "plan",
        "cron_expression": "0 6 * * *", "enabled": False,
    }, headers=auth_headers)
    assert sch.status_code == 200, sch.text
    return sch.json()["data"]


class TestBatch164ScheduleStale:
    def test_reap_marks_stale_run_failed(self, db_session, client, auth_headers):
        sched = _create_manual_schedule(client, auth_headers)
        run = _TestScheduleRun(
            schedule_id=sched["id"], status="running",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=60),
            heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        db_session.add(run)
        db_session.commit()
        reaped = _reap(db_session)
        assert reaped >= 1
        db_session.refresh(run)
        assert run.status == "failed"
        assert "stale" in run.error_message

    def test_reap_keeps_fresh_run(self, db_session, client, auth_headers):
        sched = _create_manual_schedule(client, auth_headers)
        run = _TestScheduleRun(
            schedule_id=sched["id"], status="running",
            started_at=datetime.now(timezone.utc),
            heartbeat_at=datetime.now(timezone.utc),
        )
        db_session.add(run)
        db_session.commit()
        reaped = _reap(db_session)
        assert reaped == 0
        db_session.refresh(run)
        assert run.status == "running"

    def test_reap_null_heartbeat_uses_started_at(self, db_session, client, auth_headers):
        sched = _create_manual_schedule(client, auth_headers)
        stale_legacy = _TestScheduleRun(
            schedule_id=sched["id"], status="running",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=60),
            heartbeat_at=None,
        )
        fresh_legacy = _TestScheduleRun(
            schedule_id=sched["id"], status="running",
            started_at=datetime.now(timezone.utc),
            heartbeat_at=None,
        )
        db_session.add_all([stale_legacy, fresh_legacy])
        db_session.commit()
        reaped = _reap(db_session)
        assert reaped >= 1
        db_session.refresh(stale_legacy)
        db_session.refresh(fresh_legacy)
        assert stale_legacy.status == "failed"
        assert fresh_legacy.status == "running"

    def test_trigger_immediate_and_retrigger_after_reap(self, db_session, client, auth_headers):
        sched = _create_manual_schedule(client, auth_headers)
        # 首次触发：立即返回 + run 落库（后台线程在生产库执行；测试内存库仅验证响应与落库）
        r1 = client.post(f"/api/v1/schedules/{sched['id']}/trigger", json={}, headers=auth_headers)
        assert r1.status_code == 200, r1.text
        data1 = r1.json()["data"]
        assert data1["triggered"] is True
        assert data1["status"] == "started"
        assert data1["run_id"] > 0
        runs = client.get(f"/api/v1/schedules/{sched['id']}/runs", headers=auth_headers).json()["data"]["items"]
        assert any(x["id"] == data1["run_id"] for x in runs)

        # 模拟后台线程完成首个 run（测试内存库下后台线程不可见）
        first_run = db_session.get(_TestScheduleRun, data1["run_id"])
        if first_run is not None:
            first_run.status = "failed"
            db_session.commit()

        # 构造 stale run → 回收（stale 判定的 heartbeat 逻辑由前 3 项测试覆盖）
        stale = _TestScheduleRun(
            schedule_id=sched["id"], status="running",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=60),
            heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        db_session.add(stale)
        db_session.commit()
        assert _reap(db_session) >= 1
        db_session.refresh(stale)
        assert stale.status == "failed"
        # 回收后不再 already_running → 可再次触发
        r2 = client.post(f"/api/v1/schedules/{sched['id']}/trigger", json={}, headers=auth_headers)
        assert r2.status_code == 200, r2.text
        assert r2.json()["data"]["triggered"] is True
