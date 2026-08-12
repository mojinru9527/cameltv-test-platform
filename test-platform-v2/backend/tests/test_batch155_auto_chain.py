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


class TestBatch161AutoChainRobustness:
    """Batch 161：自动链路补强回归（单条缺陷失败不阻断 + batch-execute 触发）。"""

    def test_auto_chain_survives_single_defect_error(self, db_session, client, auth_headers, monkeypatch):
        """单条缺陷创建失败时，报告与通知仍执行（G2 补强）。"""
        from app.services.test_plan_service import run_failure_auto_chain

        case = _create_case(client, auth_headers)
        plan = _create_plan(client, auth_headers, auto=True)
        _add_case_and_failed_execution(db_session, client, auth_headers, plan["id"], case["id"])

        calls = []
        def fake_notify(db, project_id, event, data):
            calls.append((project_id, event, data))
        monkeypatch.setattr("app.services.notify_service.notify_sync", fake_notify)

        real_create = None
        import app.services.defect_service as ds
        real_create = ds.create_defect
        def boom_create(db, data, creator_id, project_id):
            raise ValueError("B161TMP-缺陷创建失败（模拟）")
        monkeypatch.setattr("app.services.defect_service.create_defect", boom_create)

        result = run_failure_auto_chain(db_session, plan["id"], project_id=1, creator_id=1)
        assert result["total_failures"] >= 1
        assert result["defects_created"] == 0
        assert len(result.get("defect_errors", [])) >= 1
        assert result["report_id"] is not None
        assert any(event == "plan_failed" for _, event, _ in calls)

    def test_batch_execute_fail_triggers_auto_chain(self, db_session, client, auth_headers, monkeypatch):
        """手动批量标记失败也进入失败自动链路（G2：batch-execute 触发）。"""
        from app.api.v1 import test_plan as api_module

        case = _create_case(client, auth_headers)
        plan = _create_plan(client, auth_headers, auto=True)
        added = client.post(
            f"/api/v1/test-plans/{plan['id']}/cases",
            json={"case_ids": [case["id"]]},
            headers=auth_headers,
        )
        assert added.status_code == 200
        pc = db_session.query(_TestPlanCase).filter(_TestPlanCase.plan_id == plan["id"]).one()

        calls = []
        def fake_chain(plan_id, project_id, creator_id):
            calls.append((plan_id, project_id, creator_id))
        monkeypatch.setattr(api_module, "_run_failure_auto_chain_in_new_session", fake_chain)

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/batch-execute",
            json={"pcase_ids": [pc.id], "status": "fail", "actual_result": "B161TMP-失败", "notes": "触发链路"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["failed"] == 1
        assert any(pid == plan["id"] for pid, _, _ in calls), f"auto chain not triggered: {calls}"

    def test_batch_execute_pass_does_not_trigger_chain(self, db_session, client, auth_headers, monkeypatch):
        """批量标记通过不触发失败链路。"""
        from app.api.v1 import test_plan as api_module

        case = _create_case(client, auth_headers)
        plan = _create_plan(client, auth_headers, auto=True)
        added = client.post(
            f"/api/v1/test-plans/{plan['id']}/cases",
            json={"case_ids": [case["id"]]},
            headers=auth_headers,
        )
        assert added.status_code == 200
        pc = db_session.query(_TestPlanCase).filter(_TestPlanCase.plan_id == plan["id"]).one()

        calls = []
        def fake_chain(plan_id, project_id, creator_id):
            calls.append((plan_id, project_id, creator_id))
        monkeypatch.setattr(api_module, "_run_failure_auto_chain_in_new_session", fake_chain)

        resp = client.post(
            f"/api/v1/test-plans/{plan['id']}/batch-execute",
            json={"pcase_ids": [pc.id], "status": "pass", "actual_result": "B161TMP-通过", "notes": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["failed"] == 0
        assert calls == []
