"""Batch 155 回归：C147-6 失败自动转缺陷/报告/通知（P1-07 代码实现）。"""
from __future__ import annotations

import json
from datetime import datetime

from app.models.test_plan import TestExecution as _TestExecution, TestPlanCase as _TestPlanCase
from app.models.test_case import TestCase as _TestCase


def _create_case(client, auth_headers, *, title="B155TMP-用例", case_type="manual"):
    resp = client.post("/api/v1/test-cases", json={"title": title, "case_type": case_type}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _create_plan(client, auth_headers, *, name="B155TMP-计划", auto=False):
    resp = client.post(
        "/api/v1/test-plans",
        json={"name": name, "auto_defect_on_fail": auto},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["auto_defect_on_fail"] is auto
    return data


def _add_case_and_failed_execution(db_session, client, auth_headers, plan_id, case_id):
    add = client.post(
        f"/api/v1/test-plans/{plan_id}/cases",
        json={"case_ids": [case_id]},
        headers=auth_headers,
    )
    assert add.status_code == 200
    assert add.json()["data"]["added"] == 1
    pc = db_session.query(_TestPlanCase).filter(_TestPlanCase.plan_id == plan_id).one()
    exec_row = _TestExecution(
        plan_case_id=pc.id,
        executor_id=1,
        status="fail",
        actual_result=json.dumps({"error": "SERVER ERROR 502 bad gateway", "status_code": 502}),
        notes="B155TMP-失败",
        trace_id="",
        status_code=502,
        error_type="EXECUTION_ERROR",
        error_message="SERVER ERROR 502 bad gateway",
        executed_at=datetime.now(),
    )
    db_session.add(exec_row)
    db_session.commit()
    return pc.id


class TestPlanAutoDefectSwitch:
    """C147-6：auto_defect_on_fail 字段贯通 + 自动链路。"""

    def test_plan_switch_roundtrip(self, client, auth_headers):
        plan = _create_plan(client, auth_headers, auto=True)
        got = client.get(f"/api/v1/test-plans/{plan['id']}", headers=auth_headers).json()["data"]
        assert got["auto_defect_on_fail"] is True

    def test_auto_chain_creates_defect_report_notify(self, db_session, client, auth_headers, monkeypatch):
        from app.services.test_plan_service import run_failure_auto_chain

        case = _create_case(client, auth_headers)
        plan = _create_plan(client, auth_headers, auto=True)
        _add_case_and_failed_execution(db_session, client, auth_headers, plan["id"], case["id"])

        calls = []
        def fake_notify(db, project_id, event, data):
            calls.append((project_id, event, data))
        monkeypatch.setattr("app.services.notify_service.notify_sync", fake_notify)

        result = run_failure_auto_chain(db_session, plan["id"], project_id=1, creator_id=1)
        assert result["total_failures"] >= 1
        assert result["defects_created"] >= 1

        defects = client.get("/api/v1/defects", headers=auth_headers).json()["data"]["items"]
        auto_defects = [d for d in defects if d["title"].startswith("[AI分诊]")]
        assert len(auto_defects) >= 1
        assert auto_defects[0]["execution_id"] > 0

        reports = client.get("/api/v1/reports", headers=auth_headers).json()["data"]["items"]
        auto_reports = [r for r in reports if "失败自动报告" in r["name"]]
        assert len(auto_reports) >= 1

        assert any(event == "plan_failed" for _, event, _ in calls)

    def test_auto_chain_skipped_when_switch_off(self, db_session, client, auth_headers, monkeypatch):
        from app.services.test_plan_service import run_failure_auto_chain

        case = _create_case(client, auth_headers)
        plan = _create_plan(client, auth_headers, auto=False)
        _add_case_and_failed_execution(db_session, client, auth_headers, plan["id"], case["id"])

        calls = []
        def fake_notify(db, project_id, event, data):
            calls.append((project_id, event, data))
        monkeypatch.setattr("app.services.notify_service.notify_sync", fake_notify)

        result = run_failure_auto_chain(db_session, plan["id"], project_id=1, creator_id=1)
        assert result.get("skipped") == "auto_defect_on_fail=false"

        defects = client.get("/api/v1/defects", headers=auth_headers).json()["data"]["items"]
        assert not [d for d in defects if d["title"].startswith("[AI分诊]")]
        reports = client.get("/api/v1/reports", headers=auth_headers).json()["data"]["items"]
        assert not [r for r in reports if "失败自动报告" in r["name"]]
        assert calls == []


