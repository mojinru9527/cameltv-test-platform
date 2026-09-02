"""Batch 220 / B10 — 主链路黑盒走查（API 级，无指导跑通并放行）。

模拟黑盒测试工程师：登录 → 建任务 → 审方案 → 确认 → 执行 → 放行。
每个断言即用户可见结果；失败即卡点，本批需修复。
"""
from __future__ import annotations

from app.services import version_task_service


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


def test_mainline_blackbox_walkthrough(client, auth_headers):
    """黑盒可跑通并放行：建任务→审方案→确认→执行→放行。"""
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


def test_mainline_service_walkthrough(db_session):
    """service 级主链路：建任务→方案→审→运行→放行→知识包。"""
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
