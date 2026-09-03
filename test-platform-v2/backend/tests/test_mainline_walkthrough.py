"""Batch 220 / B10 — 主链路黑盒走查（API 级，无指导跑通并放行）。

模拟黑盒测试工程师：登录 → 建任务 → 审方案 → 确认 → 执行 → 放行。
每个断言即用户可见结果；失败即卡点，本批需修复。
"""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.services import version_task_exec_service, version_task_service


def _successful_execution(*_args, **_kwargs):
    return {
        "status": "pass",
        "reason": None,
        "evidence": [{"type": "RESPONSE", "ref": "test", "status": "pass"}],
        "failure": None,
        "http_status": 200,
        "asserts": [{"type": "status", "expected": 200, "ok": True}],
        "error": None,
    }


def _create_task(client, headers, title="v2.6 提测验收", version="2.6.0", modules="登录, 支付"):
    r = client.post(
        "/api/v1/version-tasks",
        json={"title": title, "version": version, "scope": {"modules": modules.split(", ")}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def _plan(client, headers, tid):
    rp = client.post(
        f"/api/v1/version-tasks/{tid}/plan/generate",
        json=[
            {"item_type": "functional", "title": "登录主流程", "confidence": 80},
            {"item_type": "api", "title": "POST /login 契约", "confidence": 70},
        ],
        headers=headers,
    )
    assert rp.status_code == 200, rp.text
    return [i["id"] for i in rp.json()["data"]]


def test_mainline_blackbox_walkthrough(client, auth_headers, monkeypatch):
    """黑盒可跑通并放行：建任务→审方案→确认→执行→放行。"""
    monkeypatch.setattr(version_task_exec_service, "execute_item", _successful_execution)
    h = auth_headers
    # 1. 建任务
    tid = _create_task(client, h)
    # 2. 审方案（生成 + 逐条采纳）
    plan_ids = _plan(client, h, tid)
    for pid in plan_ids:
        rr = client.post(f"/api/v1/version-tasks/{tid}/plan/{pid}/review", json={"action": "adopt"}, headers=h)
        assert rr.status_code == 200, rr.text
    # 3. 确认（进入待审）
    conf = client.post(f"/api/v1/version-tasks/{tid}/transition", json={"status": "plan_review"}, headers=h)
    assert conf.status_code == 200, conf.text
    assert conf.json()["data"]["status"] == "plan_review"
    # 4. 执行
    run = client.post(f"/api/v1/version-tasks/{tid}/run", headers=h)
    assert run.status_code == 200, run.text
    assert run.json()["data"]["progress"] == 100
    # 5. 放行
    rel = client.post(
        f"/api/v1/version-tasks/{tid}/release",
        json={"verdict": "pass", "release_bundle_id": 1, "risk": [], "summary": "主链路跑通"},
        headers=h,
    )
    assert rel.status_code == 200, rel.text
    assert rel.json()["data"]["verdict"] == "pass"
    # 6. 证据包可读
    pkg = client.get(f"/api/v1/version-tasks/{tid}/release-package", headers=h)
    assert pkg.status_code == 200
    assert pkg.json()["data"]["total_checks"] >= 1


def test_mainline_service_walkthrough(db_session, monkeypatch):
    """service 级主链路：建任务→方案→审→运行→放行→知识包。"""
    monkeypatch.setattr(version_task_exec_service, "execute_item", _successful_execution)
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(
        db_session, task.id,
        [{"item_type": "functional", "title": "登录", "confidence": 80}],
    )
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")
    version_task_service.start_run(db_session, task.id)
    package = version_task_service.release_task(db_session, task.id, verdict="pass", release_bundle_id=2)
    assert package["verdict"] == "pass"
    assert package["release_bundle_id"] == 2
    assert package["total_checks"] >= 1


def test_unexecutable_plan_is_blocked_and_cannot_pass(db_session):
    """无真实执行目标必须计为阻塞，且不能以 pass 污染版本知识。"""
    task = version_task_service.create_task(db_session, project_id=7, title="t", version="16.0.0")
    [item] = version_task_service.generate_plan(
        db_session,
        task.id,
        [{"item_type": "functional", "title": "篮球 Box Score", "confidence": 90}],
    )
    version_task_service.review_plan_item(db_session, item.id, "adopt")

    run = version_task_service.start_run(db_session, task.id)

    assert run.status == "blocked"
    assert run.total == 1
    assert run.passed == 0
    assert run.failed == 0
    assert run.skipped == 0
    assert run.blocked == 1
    defect = version_task_service.create_defect_draft(db_session, run.id, 0)
    assert defect.project_id == 7
    with pytest.raises(APIException, match="存在未通过或未执行"):
        version_task_service.release_task(db_session, task.id, verdict="pass")
    assert version_task_service.get_knowledge_record(db_session, task.id) == {}


def test_empty_plan_is_blocked_and_cannot_pass(db_session):
    task = version_task_service.create_task(db_session, project_id=7, title="t", version="16.0.1")

    run = version_task_service.start_run(db_session, task.id)

    assert run.status == "blocked"
    assert run.total == 0
    with pytest.raises(APIException, match="没有真实通过的检查"):
        version_task_service.release_task(db_session, task.id, verdict="pass")


def test_conditional_release_risk_round_trips_as_list(client, auth_headers):
    """放行风险存为列表后，任务详情仍应可读取，不能返回 500。"""
    tid = _create_task(client, auth_headers, title="体育条件放行", version="16.0.2")
    run = client.post(f"/api/v1/version-tasks/{tid}/run", headers=auth_headers)
    assert run.status_code == 200

    released = client.post(
        f"/api/v1/version-tasks/{tid}/release",
        json={"verdict": "conditional", "risk": ["无可执行目标"]},
        headers=auth_headers,
    )
    assert released.status_code == 200
    assert released.json()["data"]["risk"] == ["无可执行目标"]

    detail = client.get(f"/api/v1/version-tasks/{tid}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["risk"] == ["无可执行目标"]
