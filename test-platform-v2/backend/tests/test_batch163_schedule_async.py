"""Batch 163 / C162-1 — 调度触发异步化回归测试。"""
from __future__ import annotations

import time

from app.models.test_schedule import TestScheduleRun as _TestScheduleRun


def _create_manual_schedule(client, auth_headers):
    # 手工计划（无 API 用例）→ 不需要环境
    case = client.post("/api/v1/test-cases", json={"title": "B163TMP-用例", "case_type": "manual"}, headers=auth_headers)
    assert case.status_code == 200, case.text
    plan = client.post("/api/v1/test-plans", json={"name": "B163TMP-计划"}, headers=auth_headers)
    assert plan.status_code == 200, plan.text
    plan_id = plan.json()["data"]["id"]
    add = client.post(f"/api/v1/test-plans/{plan_id}/cases", json={"case_ids": [case.json()["data"]["id"]]}, headers=auth_headers)
    assert add.status_code == 200, add.text
    sch = client.post("/api/v1/schedules", json={
        "name": "B163TMP-调度", "plan_id": plan_id, "job_type": "plan",
        "cron_expression": "0 5 * * *", "enabled": False,
    }, headers=auth_headers)
    assert sch.status_code == 200, sch.text
    return sch.json()["data"]


class TestBatch163ScheduleAsync:
    def test_trigger_returns_immediately_with_run_id(self, db_session, client, auth_headers):
        sched = _create_manual_schedule(client, auth_headers)
        t0 = time.time()
        resp = client.post(f"/api/v1/schedules/{sched['id']}/trigger", json={}, headers=auth_headers)
        elapsed = time.time() - t0
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["triggered"] is True
        assert data["status"] == "started"
        assert data["run_id"] > 0
        assert elapsed < 5, f"trigger 应快速返回，实际 {elapsed:.1f}s"
        # run 已落库（running 或已快速完成）
        runs = client.get(f"/api/v1/schedules/{sched['id']}/runs", headers=auth_headers).json()["data"]["items"]
        assert any(r["id"] == data["run_id"] for r in runs)

    def test_trigger_duplicate_running_rejected(self, db_session, client, auth_headers):
        sched = _create_manual_schedule(client, auth_headers)
        run = _TestScheduleRun(schedule_id=sched["id"], status="running")
        db_session.add(run)
        db_session.commit()
        resp = client.post(f"/api/v1/schedules/{sched['id']}/trigger", json={}, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["triggered"] is False
        assert data["reason"] == "already_running"
        assert data["run_id"] == run.id
