"""Batch 216 / B6 — VersionTask 唯一事实源 + 状态机 + API + 旧数据兼容映射。"""
from __future__ import annotations

import pytest

from app.models.version_mission import VersionMission
from app.models.version_task import VersionTask, VersionTaskDefect, VersionTaskExecution
from app.services import version_task_service
from app.core.exceptions import APIException


# ────────────────────────────── 模型 / Service ──────────────────────────────

def test_create_and_transition_state_machine(db_session):
    task = version_task_service.create_task(
        db_session, project_id=1, title="v2.6 验收", version="2.6.0", qa_owner_id=7
    )
    assert task.status == "draft"

    # 合法流转
    assert version_task_service.transition_task(db_session, task.id, "plan_review").status == "plan_review"
    assert version_task_service.transition_task(db_session, task.id, "approved").status == "approved"
    assert version_task_service.transition_task(db_session, task.id, "executing").status == "executing"
    executed = version_task_service.transition_task(db_session, task.id, "executed")
    assert executed.status == "executed"
    verdict = version_task_service.transition_task(db_session, task.id, "verdict")
    assert verdict.status == "verdict"
    released = version_task_service.transition_task(db_session, task.id, "released")
    assert released.status == "released"
    # 未显式给结论时，放行自动补 pass
    assert released.verdict == "pass"

    # 非法流转被拒绝
    with pytest.raises(APIException):
        version_task_service.transition_task(db_session, task.id, "draft")


def test_blocked_rework(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    version_task_service.transition_task(db_session, task.id, "plan_review")
    version_task_service.transition_task(db_session, task.id, "blocked")
    assert version_task_service.transition_task(db_session, task.id, "draft").status == "draft"


def test_execution_and_defect_links(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    link = version_task_service.add_execution(db_session, task.id, "runner", 42, ref="run://1")
    assert link.task_id == task.id
    task = version_task_service.get_task(db_session, task.id)
    assert len(task.executions) == 1

    dlink = version_task_service.add_defect(db_session, task.id, 99)
    assert dlink.task_id == task.id
    task = version_task_service.get_task(db_session, task.id)
    assert len(task.defects) == 1


def test_compat_mission_view_no_double_write(db_session):
    mission = VersionMission(
        project_id=1, mission_key="m-1", title="旧智能任务", version="3.0.0",
        summary="old", created_by=1, qa_owner_id=2, scope='{"modules":[]}',
    )
    db_session.add(mission)
    db_session.commit()

    view = version_task_service.compat_mission_view(db_session, mission.id)
    assert view["source"] == "mission"
    assert view["source_mission_id"] == mission.id
    assert view["legacy"] is True
    # 兼容映射不写库：db 中不存在来自 mission 的 version_task 行
    assert db_session.query(VersionTask).filter_by(source="mission").count() == 0


# ────────────────────────────── API ──────────────────────────────

def test_api_crud_and_transition(client, auth_headers):
    h = auth_headers
    todo = {
        "title": "v3.1 提测验收", "version": "3.1.0",
        "scope": {"modules": ["登录", "支付"]}, "qa_owner_id": 3,
    }
    r = client.post("/api/v1/version-tasks", json=todo, headers=h)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    tid = data["id"]
    assert data["status"] == "draft"
    assert data["scope"]["modules"] == ["登录", "支付"]

    # list
    rl = client.get("/api/v1/version-tasks", headers=h)
    assert rl.status_code == 200
    assert rl.json()["data"]["total"] >= 1

    # detail
    rd = client.get(f"/api/v1/version-tasks/{tid}", headers=h)
    assert rd.status_code == 200
    assert rd.json()["data"]["id"] == tid

    # transition chain
    for s in ("plan_review", "approved", "executing", "executed", "verdict"):
        rr = client.post(
            f"/api/v1/version-tasks/{tid}/transition",
            json={"status": s, "verdict": "conditional"} if s == "verdict" else {"status": s},
            headers=h,
        )
        assert rr.status_code == 200, rr.text
        assert rr.json()["data"]["status"] == s

    # link execution
    rex = client.post(
        f"/api/v1/version-tasks/{tid}/executions",
        json={"execution_type": "runner", "execution_id": 5, "ref": "run://5"},
        headers=h,
    )
    assert rex.status_code == 200


def test_api_illegal_transition(client, auth_headers):
    h = auth_headers
    r = client.post("/api/v1/version-tasks", json={"title": "t", "version": "1.0"}, headers=h)
    tid = r.json()["data"]["id"]
    # draft -> released 非法
    rr = client.post(f"/api/v1/version-tasks/{tid}/transition", json={"status": "released"}, headers=h)
    assert rr.status_code == 200 and rr.json().get("code") != 0



# ────────────────────────────── B7: 验收方案生成 + 审核面板 ──────────────────────────────

def test_plan_generate_and_review(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(
        db_session, task.id,
        [
            {"item_type": "functional", "title": "登录", "confidence": 80},
            {"item_type": "api", "title": "POST /login", "confidence": 60, "question": "鉴权方式？"},
        ],
    )
    assert len(items) == 2

    adopted = version_task_service.review_plan_item(db_session, items[0].id, "adopt")
    assert adopted.status == "adopted"
    modified = version_task_service.review_plan_item(
        db_session, items[1].id, "modify", patch={"title": "POST /login(新版)", "confidence": 90}
    )
    assert modified.status == "modified"
    assert modified.title == "POST /login(新版)"
    assert modified.confidence == 90

    asked = version_task_service.review_plan_item(
        db_session, items[1].id, "ask", patch={"question": "token 过期策略?"}
    )
    assert asked.status == "asked"

    removed = version_task_service.review_plan_item(db_session, items[0].id, "remove")
    assert removed.status == "removed"


def test_api_plan_generate_and_review(client, auth_headers):
    h = auth_headers
    r = client.post("/api/v1/version-tasks", json={"title": "t", "version": "1.0"}, headers=h)
    tid = r.json()["data"]["id"]
    rp = client.post(
        f"/api/v1/version-tasks/{tid}/plan/generate",
        json=[{"item_type": "functional", "title": "登录", "confidence": 85}],
        headers=h,
    )
    assert rp.status_code == 200, rp.text
    assert len(rp.json()["data"]) == 1
    item_id = rp.json()["data"][0]["id"]

    rr = client.post(
        f"/api/v1/version-tasks/{tid}/plan/{item_id}/review",
        json={"action": "adopt"},
        headers=h,
    )
    assert rr.status_code == 200
    assert rr.json()["data"]["status"] == "adopted"

    rl = client.get(f"/api/v1/version-tasks/{tid}/plan", headers=h)
    assert rl.status_code == 200


# ────────────────────────────── B8: 一键运行 + 证据 + 失败分类→缺陷草稿 ──────────────────────────────

def test_start_run_and_coverage_writeback(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(
        db_session, task.id,
        [{"item_type": "functional", "title": "登录", "confidence": 80},
         {"item_type": "api", "title": "POST /login", "confidence": 60}],
    )
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")

    run = version_task_service.start_run(db_session, task.id)
    assert run.status in ("done", "failed")
    assert run.progress == 100
    assert run.passed + run.failed + run.skipped + run.blocked == run.total >= 1
    # coverage 回写（C217-1）
    refreshed = version_task_service.get_task(db_session, task.id)
    cov = refreshed.coverage
    assert "pass" in cov and "fail" in cov
    assert refreshed.status == "executed"


def test_defect_draft_from_failure(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(
        db_session, task.id, [{"item_type": "functional", "title": "登录", "confidence": 80}]
    )
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")
    run = version_task_service.start_run(db_session, task.id)
    assert run.failed == 1  # 末条固定失败
    defect = version_task_service.create_defect_draft(db_session, run.id, 0, creator_id=1)
    assert defect.status == "open"
    task = version_task_service.get_task(db_session, task.id)
    assert len(task.defects) >= 1


def test_api_run_and_defect(client, auth_headers):
    h = auth_headers
    r = client.post("/api/v1/version-tasks", json={"title": "t", "version": "1.0"}, headers=h)
    tid = r.json()["data"]["id"]
    rp = client.post(
        f"/api/v1/version-tasks/{tid}/plan/generate",
        json=[{"item_type": "functional", "title": "登录", "confidence": 80}],
        headers=h,
    )
    pid = rp.json()["data"][0]["id"]
    client.post(f"/api/v1/version-tasks/{tid}/plan/{pid}/review", json={"action": "adopt"}, headers=h)

    rr = client.post(f"/api/v1/version-tasks/{tid}/run", headers=h)
    assert rr.status_code == 200, rr.text
    run = rr.json()["data"]
    assert run["failed"] >= 1

    rl = client.get(f"/api/v1/version-tasks/{tid}/runs", headers=h)
    assert rl.status_code == 200
    assert len(rl.json()["data"]) >= 1

    rd = client.post(f"/api/v1/version-tasks/{tid}/runs/{run['id']}/defect/0", headers=h)
    assert rd.status_code == 200, rd.text
    assert rd.json()["data"]["status"] == "open"


# ────────────────────────────── B9: 放行证据包 + 绑定发布包 + 通知 ──────────────────────────────

def test_release_package_build(client, auth_headers):
    h = auth_headers
    r = client.post("/api/v1/version-tasks", json={"title": "t", "version": "1.0"}, headers=h)
    tid = r.json()["data"]["id"]
    rp = client.post(
        f"/api/v1/version-tasks/{tid}/plan/generate",
        json=[{"item_type": "functional", "title": "登录", "confidence": 80}],
        headers=h,
    )
    pid = rp.json()["data"][0]["id"]
    client.post(f"/api/v1/version-tasks/{tid}/plan/{pid}/review", json={"action": "adopt"}, headers=h)
    client.post(f"/api/v1/version-tasks/{tid}/run", headers=h)

    # 放行前预览
    prev = client.get(f"/api/v1/version-tasks/{tid}/release-package", headers=h)
    assert prev.status_code == 200
    assert "pass_rate" in prev.json()["data"]

    # 放行（绑定发布包）
    rel = client.post(
        f"/api/v1/version-tasks/{tid}/release",
        json={"verdict": "conditional", "release_bundle_id": 3, "risk": ["登录超时"], "summary": "有条件放行"},
        headers=h,
    )
    assert rel.status_code == 200, rel.text
    data = rel.json()["data"]
    assert data["verdict"] == "conditional"
    assert data["release_bundle_id"] == 3
    assert data["total_checks"] >= 1

    # 通知
    nt = client.post(f"/api/v1/version-tasks/{tid}/notify", headers=h)
    assert nt.status_code == 200
    assert nt.json()["data"]["sent"] is True


def test_release_service_illegal_verdict(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    with pytest.raises(APIException):
        version_task_service.release_task(db_session, task.id, verdict="noop")


# ────────────────────────────── B11: 版本沉淀 + 复用建议 ──────────────────────────────

def test_release_auto_records_knowledge(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(db_session, task.id, [{"item_type": "functional", "title": "登录"}])
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")
    version_task_service.start_run(db_session, task.id)
    version_task_service.release_task(db_session, task.id, verdict="pass", release_bundle_id=2)
    rec = version_task_service.record_version_knowledge(db_session, task.id)
    assert rec.version == "1.0"
    assert rec.verdict == "pass"
    suggestions = version_task_service.get_reuse_suggestions(db_session, project_id=1)
    assert len(suggestions) >= 1
    assert "登录" in " ".join(suggestions[0]["reuse"])


def test_api_reuse_suggestions(client, auth_headers):
    h = auth_headers
    r = client.get("/api/v1/version-tasks/knowledge/reuse", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


# ────────────────────────────── B12: 推荐回归集 + 缺陷同步 ──────────────────────────────

def test_recommend_regression_set(db_session):
    task = version_task_service.create_task(
        db_session, project_id=1, title="t", version="1.0", scope={"modules": ["登录", "支付"]}
    )
    items = version_task_service.generate_plan(db_session, task.id, [{"item_type": "functional", "title": "登录主流程", "confidence": 80}])
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")
    recs = version_task_service.recommend_regression_set(db_session, task.id)
    titles = [r["title"] for r in recs]
    assert "登录主流程" in titles
    assert "登录 回归" in titles
    assert "支付 回归" in titles


def test_sync_defect_notification(db_session):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    result = version_task_service.sync_defect_notification(db_session, task.id, 99)
    assert result["synced"] is True
    assert result["defect_id"] == 99


def test_api_regression_set(client, auth_headers):
    h = auth_headers
    r = client.post("/api/v1/version-tasks", json={"title": "t", "version": "1.0", "scope": {"modules": ["登录"]}}, headers=h)
    tid = r.json()["data"]["id"]
    rr = client.get(f"/api/v1/version-tasks/{tid}/regression-set", headers=h)
    assert rr.status_code == 200
    assert isinstance(rr.json()["data"], list)


# ────────────────────────────── B13: 运营指标 + 跨版本对比 ──────────────────────────────

def test_operations_metrics_and_compare(db_session):
    for v in ("1.0", "2.0"):
        task = version_task_service.create_task(db_session, project_id=1, title=f"t{v}", version=v)
        items = version_task_service.generate_plan(db_session, task.id, [{"item_type": "functional", "title": "登录"}])
        for it in items:
            version_task_service.review_plan_item(db_session, it.id, "adopt")
        version_task_service.start_run(db_session, task.id)
        version_task_service.release_task(db_session, task.id, verdict="pass", release_bundle_id=1)
    metrics = version_task_service.get_operations_metrics(db_session, project_id=1)
    assert metrics["released_count"] == 2
    assert metrics["total_tasks"] == 2
    compare = version_task_service.compare_versions(db_session, 1, "1.0", "2.0")
    assert compare["a"]["exists"] is True
    assert compare["b"]["exists"] is True


def test_api_metrics_and_compare(client, auth_headers):
    h = auth_headers
    mo = client.get("/api/v1/metrics/operations", headers=h)
    assert mo.status_code == 200
    assert "released_count" in mo.json()["data"]
    cmp = client.get("/api/v1/version-tasks/compare?version_a=1.0&version_b=2.0", headers=h)
    assert cmp.status_code == 200
    assert "a" in cmp.json()["data"]
