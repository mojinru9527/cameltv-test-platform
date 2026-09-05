"""Batch 216 / B6 — VersionTask 唯一事实源 + 状态机 + API + 旧数据兼容映射。"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from app.models.version_mission import VersionMission
from app.models.version_task import VersionTask, VersionTaskDefect, VersionTaskExecution
from app.services import version_task_service
from app.core.exceptions import APIException


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

def test_start_run_and_coverage_writeback(db_session, monkeypatch):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(
        db_session, task.id,
        [{"item_type": "functional", "title": "登录", "confidence": 80},
         {"item_type": "api", "title": "POST /login", "confidence": 60, "exec_meta": {"method": "POST", "url": "http://127.0.0.1:9/login"}}],
    )
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")

    # F-02：真实执行（monkeypatch execute_item 模拟真实 HTTP 判定），不再臆造
    import app.services.version_task_exec_service as exec_svc

    def fake_execute(db, item, base_url):
        if item.item_type == "api":
            return {"status": "fail", "evidence": [], "failure": {"kind": "business", "message": "断言失败"}, "http_status": 500}
        return {"status": "pass", "evidence": [{"type": "RESPONSE", "status": "pass"}], "failure": None, "http_status": 200}

    monkeypatch.setattr(exec_svc, "execute_item", fake_execute)

    run = version_task_service.start_run(db_session, task.id)
    assert run.status in ("done", "failed")
    assert run.progress == 100
    assert run.passed + run.failed + run.skipped + run.blocked == run.total >= 1
    assert run.passed == 1 and run.failed == 1
    # coverage 回写（C217-1）
    refreshed = version_task_service.get_task(db_session, task.id)
    cov = refreshed.coverage
    assert "pass" in cov and "fail" in cov and "skip" in cov
    assert refreshed.status == "executed"


def test_defect_draft_from_failure(db_session, monkeypatch):
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(
        db_session, task.id, [{"item_type": "functional", "title": "登录", "confidence": 80}]
    )
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")

    import app.services.version_task_exec_service as exec_svc

    monkeypatch.setattr(
        exec_svc, "execute_item",
        lambda db, item, base_url: {"status": "fail", "evidence": [], "failure": {"kind": "business", "message": "登录失败"}, "http_status": 500},
    )
    run = version_task_service.start_run(db_session, task.id)
    assert run.failed == 1  # 真实失败（非臆造）
    defect = version_task_service.create_defect_draft(db_session, run.id, 0, creator_id=1)
    assert defect.status == "open"
    task = version_task_service.get_task(db_session, task.id)
    assert len(task.defects) >= 1


def test_api_run_and_defect(client, auth_headers, monkeypatch):
    import app.services.version_task_exec_service as exec_svc

    monkeypatch.setattr(
        exec_svc, "execute_item",
        lambda db, item, base_url: {"status": "fail", "evidence": [], "failure": {"kind": "business", "message": "boom"}, "http_status": 500},
    )
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

def test_release_auto_records_knowledge(db_session, monkeypatch):
    from app.services import version_task_exec_service

    monkeypatch.setattr(version_task_exec_service, "execute_item", _successful_execution)
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

def test_operations_metrics_and_compare(db_session, monkeypatch):
    from app.services import version_task_exec_service

    monkeypatch.setattr(version_task_exec_service, "execute_item", _successful_execution)
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


# ────────────────────────────── B14: D 级收敛（归档/资产视图/数据合并） ──────────────────────────────

def test_convergence_archive_and_views(db_session):
    from app.models.test_plan import TestPlan
    from app.services import convergence_service
    plan = TestPlan(project_id=1, name="旧测试计划", status="active")
    db_session.add(plan)
    db_session.commit()
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    res = convergence_service.archive_test_plan(db_session, plan.id, task.id)
    assert res["status"] == "archived"
    assert res["converged_to_task"] == task.id
    view = convergence_service.unified_assets_view(db_session, 1)
    assert view["single_fact_source"] == "version_task"
    assert any(p["archived"] for p in view["test_plans"])
    data = convergence_service.merged_data_assets(db_session, 1)
    assert "data_assets" in data


def test_api_convergence(client, auth_headers):
    h = auth_headers
    r = client.get("/api/v1/convergence/assets", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["single_fact_source"] == "version_task"


# ────────────────────────────── B15: 新业务接入向导 + 基线 ──────────────────────────────

def test_business_onboarding_baseline(db_session, monkeypatch):
    from app.models.api_asset import ApiEndpoint
    from app.models.requirement import RequirementDocument
    from app.services import onboarding_service, openapi_import_service, version_task_exec_service

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Basketball", "version": "16.0.0"},
        "paths": {
            "/box-score": {
                "get": {
                    "summary": "篮球 Box Score",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    monkeypatch.setattr(
        openapi_import_service, "resolve_openapi_spec", lambda _url: spec, raising=False
    )

    def _plan(db, task_id, _project_id):
        return version_task_service.generate_plan(
            db,
            task_id,
            [{
                "item_type": "api",
                "title": "篮球 Box Score",
                "confidence": 95,
                "exec_meta": {
                    "method": "GET",
                    "path": "/box-score",
                    "assert": [{"type": "status", "expected": 200}],
                },
            }],
        )

    monkeypatch.setattr(version_task_service, "ai_generate_plan", _plan)
    monkeypatch.setattr(
        version_task_exec_service,
        "execute_item",
        lambda *_args, **_kwargs: {
            "status": "pass",
            "reason": None,
            "evidence": [{"type": "RESPONSE", "status": "pass"}],
            "failure": None,
            "http_status": 200,
            "asserts": [{"type": "status", "expected": 200, "ok": True}],
            "error": None,
        },
    )
    ob = onboarding_service.create_onboarding(
        db_session,
        1,
        name="basketball",
        service_key="basketball-service",
        version="16.0.0",
        requirement_text="验证篮球比赛详情、比分和异常状态。",
        api_spec_url="http://x/swagger.json",
        base_url="http://basketball.test",
    )
    assert ob.step == 1
    assert ob.version == "16.0.0"
    assert ob.requirement_text == "验证篮球比赛详情、比分和异常状态。"
    onboarding_service.complete_step(db_session, ob.id, 2)
    assert db_session.query(ApiEndpoint).filter_by(project_id=1).count() == 1
    task = version_task_service.get_task(db_session, ob.version_task_id)
    requirement = db_session.get(RequirementDocument, task.requirement_doc_id)
    assert task.version == "16.0.0"
    assert requirement is not None
    assert requirement.content == "验证篮球比赛详情、比分和异常状态。"
    onboarding_service.complete_step(db_session, ob.id, 3)
    assert ob.version_task_id is not None
    ob = onboarding_service.complete_step(db_session, ob.id, 4)
    assert ob.status == "active"
    baseline = json.loads(ob.baseline)
    assert baseline == {
        "task_id": ob.version_task_id,
        "run_id": baseline["run_id"],
        "status": "done",
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "blocked": 0,
    }


def test_business_onboarding_reuses_matching_version_task(db_session, monkeypatch):
    from app.models.requirement import RequirementDocument
    from app.models.version_task import VersionTask
    from app.services import onboarding_service, openapi_import_service, requirement_service

    requirement_text = "验证体育 16.0.0 比赛与文章链路。"
    requirement = requirement_service.create_requirement(
        db_session,
        project_id=1,
        title="体育平台 16.0.0 接入需求",
        file_type="manual",
        source_ref="onboarding",
        content=requirement_text,
    )
    existing_task = version_task_service.create_task(
        db_session,
        project_id=1,
        title="体育平台 16.0.0 业务基线",
        version="16.0.0",
        source="onboarding",
        requirement_doc_id=requirement["id"],
        scope={"modules": ["已有范围"]},
    )
    monkeypatch.setattr(
        openapi_import_service,
        "resolve_openapi_spec",
        lambda _url: {
            "openapi": "3.0.0",
            "info": {"version": "16.0.0"},
            "paths": {"/scores": {"get": {"responses": {"200": {"description": "ok"}}}}},
        },
    )

    ob = onboarding_service.create_onboarding(
        db_session,
        1,
        name="体育平台",
        service_key="sports-service",
        version="16.0.0",
        requirement_text=requirement_text,
        api_spec_url="http://x/openapi.json",
        base_url="http://sports.test",
    )

    ob = onboarding_service.complete_step(db_session, ob.id, 2)

    assert ob.version_task_id == existing_task.id
    assert db_session.query(VersionTask).filter_by(project_id=1, version="16.0.0").count() == 1
    assert db_session.query(RequirementDocument).filter_by(project_id=1).count() == 1
    scope = json.loads(existing_task.scope)
    assert scope["modules"] == ["已有范围"]
    assert scope["base_url"] == "http://sports.test"
    assert scope["api_spec_url"] == "http://x/openapi.json"


def test_business_onboarding_rejects_different_requirement_for_existing_version(db_session, monkeypatch):
    from app.models.api_asset import ApiImportBatch
    from app.models.requirement import RequirementDocument
    from app.services import onboarding_service, openapi_import_service, requirement_service

    requirement = requirement_service.create_requirement(
        db_session,
        project_id=1,
        title="已有需求",
        file_type="manual",
        source_ref="manual",
        content="已有的 16.0.0 需求",
    )
    existing_task = version_task_service.create_task(
        db_session,
        project_id=1,
        title="已有版本任务",
        version="16.0.0",
        requirement_doc_id=requirement["id"],
    )
    monkeypatch.setattr(
        openapi_import_service,
        "resolve_openapi_spec",
        lambda _url: pytest.fail("conflicting requirements must be rejected before OpenAPI access"),
    )
    ob = onboarding_service.create_onboarding(
        db_session,
        1,
        name="体育平台",
        service_key="sports-service",
        version="16.0.0",
        requirement_text="另一份 16.0.0 需求",
        api_spec_url="http://x/openapi.json",
        base_url="http://sports.test",
    )

    with pytest.raises(APIException, match="绑定了不同的需求内容"):
        onboarding_service.complete_step(db_session, ob.id, 2)

    db_session.refresh(existing_task)
    assert existing_task.requirement_doc_id == requirement["id"]
    assert db_session.query(RequirementDocument).filter_by(project_id=1).count() == 1
    assert db_session.query(ApiImportBatch).filter_by(project_id=1).count() == 0
    assert ob.step == 1


def test_business_onboarding_requires_real_openapi_import(db_session):
    from app.services import onboarding_service

    ob = onboarding_service.create_onboarding(
        db_session, 1, name="football", service_key="football-service"
    )

    with pytest.raises(APIException, match="OpenAPI"):
        onboarding_service.complete_step(db_session, ob.id, 2)
    assert ob.version_task_id is None
    assert ob.step == 1

    with pytest.raises(APIException, match="按顺序"):
        onboarding_service.complete_step(db_session, ob.id, 3)


def test_business_onboarding_rejects_steps_after_completion(db_session):
    from app.services import onboarding_service

    ob = onboarding_service.create_onboarding(
        db_session, 1, name="sports", service_key="sports-service"
    )
    ob.step = 4
    db_session.commit()

    with pytest.raises(APIException, match="已完成"):
        onboarding_service.complete_step(db_session, ob.id, 5)


def test_business_onboarding_blocked_run_is_not_activated(db_session, monkeypatch):
    from app.services import onboarding_service, openapi_import_service

    monkeypatch.setattr(
        openapi_import_service,
        "resolve_openapi_spec",
        lambda _url: {
            "openapi": "3.0.0",
            "info": {"version": "16.0.0"},
            "paths": {"/scores": {"get": {"responses": {"200": {"description": "ok"}}}}},
        },
        raising=False,
    )

    def _plan(db, task_id, _project_id):
        return version_task_service.generate_plan(
            db,
            task_id,
            [{"item_type": "functional", "title": "足球比分", "confidence": 80}],
        )

    monkeypatch.setattr(version_task_service, "ai_generate_plan", _plan)
    ob = onboarding_service.create_onboarding(
        db_session,
        1,
        name="football",
        service_key="football-service",
        api_spec_url="http://x/openapi.json",
    )
    onboarding_service.complete_step(db_session, ob.id, 2)
    onboarding_service.complete_step(db_session, ob.id, 3)

    ob = onboarding_service.complete_step(db_session, ob.id, 4)

    baseline = json.loads(ob.baseline)
    assert ob.status == "blocked"
    assert baseline["status"] == "blocked"
    assert baseline["passed"] == 0
    assert baseline["blocked"] == 1


def test_api_onboarding(client, auth_headers, monkeypatch):
    from app.services import openapi_import_service

    monkeypatch.setattr(
        openapi_import_service,
        "resolve_openapi_spec",
        lambda _url: {
            "openapi": "3.0.0",
            "info": {"version": "16.0.0"},
            "paths": {"/health": {"get": {"responses": {"200": {"description": "ok"}}}}},
        },
        raising=False,
    )
    monkeypatch.setattr(
        version_task_service,
        "ai_generate_plan",
        lambda db, task_id, _pid: version_task_service.generate_plan(
            db,
            task_id,
            [{
                "item_type": "api",
                "title": "健康检查",
                "confidence": 90,
                "exec_meta": {"method": "GET", "path": "/health"},
            }],
        ),
    )
    h = auth_headers
    r = client.post(
        "/api/v1/onboarding/businesses",
        json={
            "name": "camel-mimo",
            "service_key": "camel-mimo",
            "version": "16.0.0",
            "requirement_text": "验证体育 16.0.0 比赛与文章链路。",
            "api_spec_url": "http://x/openapi.json",
            "base_url": "http://sports.test",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["version"] == "16.0.0"
    assert r.json()["data"]["requirement_text"] == "验证体育 16.0.0 比赛与文章链路。"
    oid = r.json()["data"]["id"]
    # F-08: step2 接基线（创建版本任务）必须先于 step3
    assert client.post(f"/api/v1/onboarding/businesses/{oid}/steps/2", headers=h).json()["data"]["step"] == 2
    rr = client.post(f"/api/v1/onboarding/businesses/{oid}/steps/3", headers=h)
    assert rr.status_code == 200
    assert rr.json()["data"]["step"] == 3


def test_onboarding_readiness_separates_baseline_and_durable_runtime(db_session, monkeypatch):
    from app.core.config import settings
    from app.modules.aitde.common.enums import WorkerStatus
    from app.modules.aitde.workflow.models import WorkerNode
    from app.services import ai_config_service, onboarding_service

    monkeypatch.setattr(
        ai_config_service.ai_config_service,
        "resolve_out",
        lambda _db, _project_id: {
            "configured": True,
            "provider": {"id": 7, "name": "sports-ai", "model": "json-model"},
            "health": {"status": "ok", "kind": "", "message": "最近一次调用成功"},
        },
    )
    monkeypatch.setattr(settings, "temporal_enabled", False)
    db_session.add(
        WorkerNode(
            worker_key="worker-test",
            name="测试执行器",
            status=WorkerStatus.ONLINE.value,
            last_heartbeat_at=datetime.now(),
        )
    )
    db_session.commit()

    readiness = onboarding_service.get_readiness(db_session, project_id=1)

    assert readiness["baseline_ready"] is True
    assert readiness["durable_ready"] is False
    assert readiness["services"]["ai_provider"]["status"] == "ready"
    assert readiness["services"]["temporal"]["status"] == "blocked"
    assert readiness["services"]["runtime_worker"]["status"] == "ready"
    assert readiness["services"]["runtime_worker"]["managed_by"] == "platform"


def test_onboarding_readiness_does_not_treat_unverified_ai_as_ready(db_session, monkeypatch):
    from app.services import ai_config_service, onboarding_service

    monkeypatch.setattr(
        ai_config_service.ai_config_service,
        "resolve_out",
        lambda _db, _project_id: {
            "configured": True,
            "provider": {"id": 8, "name": "sports-ai", "model": "json-model"},
            "health": {"status": "unknown", "kind": "", "message": "尚未验证"},
        },
    )

    readiness = onboarding_service.get_readiness(db_session, project_id=1)

    assert readiness["baseline_ready"] is False
    assert readiness["services"]["ai_provider"]["status"] == "unknown"


def test_api_onboarding_readiness(client, auth_headers, monkeypatch):
    from app.services import onboarding_service

    monkeypatch.setattr(
        onboarding_service,
        "get_readiness",
        lambda _db, project_id: {
            "baseline_ready": False,
            "durable_ready": False,
            "services": {},
            "project_id": project_id,
        },
    )

    response = client.get("/api/v1/onboarding/readiness", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["project_id"] == 1


# ────────────────────────────── Batch 230 S2 / DEF-20260905-002 ──────────────────────────────
# 版本验收任务列表页需要「覆盖」与「更新时间」两列，此前 VersionTaskListItem
# 不回传这两个字段 → 列表页无数据源。coverage 是 Text 列存的 JSON 串，必须经
# _json_to_dict 解析，历史脏数据也不能让列表接口 500。

def test_api_list_exposes_coverage_and_updated_at(client, auth_headers, db_session):
    task = version_task_service.create_task(
        db_session, project_id=1, title="体育 16.0.0 验收", version="16.0.0"
    )
    task.coverage = json.dumps({"pass": 3, "fail": 1, "skip": 0, "blocked": 0})
    db_session.commit()

    resp = client.get("/api/v1/version-tasks", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    item = next(i for i in resp.json()["data"]["items"] if i["id"] == task.id)
    assert item["coverage"] == {"pass": 3, "fail": 1, "skip": 0, "blocked": 0}
    assert item["updated_at"] is not None


def test_list_item_tolerates_malformed_coverage():
    from app.schemas.version_task import VersionTaskListItem

    parsed = VersionTaskListItem.model_validate(
        {"id": 1, "title": "t", "version": "1.0", "coverage": "{not json"}
    )
    assert parsed.coverage == {}

    default = VersionTaskListItem.model_validate({"id": 2, "title": "t", "version": "1.0"})
    assert default.coverage == {}
    assert default.updated_at is None
