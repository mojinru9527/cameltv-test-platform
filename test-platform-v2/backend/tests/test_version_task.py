"""Batch 216 / B6 — VersionTask 唯一事实源 + 状态机 + API（平台简化批次：旧数据兼容映射已随 version_mission 删除）。"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

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


# ────────────────────────────── Batch 230 S3 / DEF-20260905-003 ──────────────────────────────
# 生产复测：方案里没有任何已采纳条目时，一键运行既跑不出标的，又把 task.status
# 无条件写成 executed，前端于是提示「运行完成：0 通过 / 0 失败」并显示「已执行」。
# 修复取 D1：阻塞原因复用 failures（新增 kind="plan"），不加顶层 reason 字段、不做迁移；
# 无采纳条目时将方案前置条件计为一条 blocked 检查，保持统计恒等式并避免「阻塞 0」。

def test_start_run_without_adopted_items_reports_plan_blockage(db_session, monkeypatch):
    import app.services.version_task_exec_service as exec_svc

    def _boom(*_args, **_kwargs):
        raise AssertionError("零采纳项时不应执行任何条目")

    monkeypatch.setattr(exec_svc, "execute_item", _boom)

    task = version_task_service.create_task(db_session, project_id=1, title="t", version="16.0.0")
    version_task_service.generate_plan(
        db_session, task.id, [{"item_type": "functional", "title": "登录", "confidence": 80}]
    )
    # 故意不采纳任何条目

    run = version_task_service.start_run(db_session, task.id)

    assert run.status == "blocked"
    assert run.total == 1
    assert run.blocked == 1
    assert run.passed == 0 and run.failed == 0 and run.skipped == 0

    failures = json.loads(run.failures or "[]")
    assert len(failures) == 1
    assert failures[0]["kind"] == "plan"
    assert failures[0]["item_id"] == 0
    assert failures[0]["http_status"] is None
    assert "采纳" in failures[0]["message"]

    # 任务不得再被标成「已执行」
    assert version_task_service.get_task(db_session, task.id).status == "blocked"


def test_start_run_marks_task_executed_when_run_done(db_session, monkeypatch):
    import app.services.version_task_exec_service as exec_svc

    monkeypatch.setattr(
        exec_svc, "execute_item", lambda db, item, base_url: _successful_execution()
    )
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    items = version_task_service.generate_plan(
        db_session, task.id, [{"item_type": "functional", "title": "登录", "confidence": 80}]
    )
    for it in items:
        version_task_service.review_plan_item(db_session, it.id, "adopt")

    run = version_task_service.start_run(db_session, task.id)

    assert run.status == "done"
    assert version_task_service.get_task(db_session, task.id).status == "executed"


def test_plan_failure_can_be_converted_to_defect_draft(db_session):
    """合成的 plan 失败项也带「转缺陷草稿」按钮，不能被 FAILURE_KINDS 拒掉。"""
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    version_task_service.generate_plan(
        db_session, task.id, [{"item_type": "functional", "title": "登录", "confidence": 80}]
    )
    run = version_task_service.start_run(db_session, task.id)
    assert json.loads(run.failures)[0]["kind"] == "plan"

    defect = version_task_service.create_defect_draft(db_session, run.id, 0, creator_id=1)

    assert defect.status == "open"
    assert "方案无可执行项" in defect.title


def test_blocked_run_task_can_be_rejected_but_not_released(db_session):
    """task.status=blocked 后仍可下「打回/有条件放行」结论；放行(pass)必须继续被拒。"""
    task = version_task_service.create_task(db_session, project_id=1, title="t", version="1.0")
    version_task_service.generate_plan(
        db_session, task.id, [{"item_type": "functional", "title": "登录", "confidence": 80}]
    )
    version_task_service.start_run(db_session, task.id)
    assert version_task_service.get_task(db_session, task.id).status == "blocked"

    with pytest.raises(APIException) as exc:
        version_task_service.release_task(db_session, task.id, "pass")
    assert "不可选择放行" in exc.value.msg

    pkg = version_task_service.release_task(db_session, task.id, "blocked")
    assert pkg["verdict"] == "blocked"
    assert pkg["status"] == "released"


# Batch 231 S2: every task-scoped route must enforce X-Project-Id, including
# nested plan/run mutations. A 404 envelope avoids revealing resource ownership.
@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("get", "", None),
        ("patch", "", {"title": "cross-project overwrite"}),
        ("post", "/transition", {"status": "cancelled"}),
        ("post", "/executions", {"execution_type": "runner", "execution_id": 1}),
        ("post", "/defects", {"defect_id": 1}),
        ("get", "/plan", None),
        ("post", "/plan/generate", [{"title": "leaked plan"}]),
        ("post", "/plan/generate-ai", None),
        ("post", "/plan/{item_id}/review", {"action": "adopt"}),
        ("post", "/run", None),
        ("get", "/runs", None),
        ("get", "/runs/{run_id}", None),
        ("post", "/runs/{run_id}/defect/0", None),
        ("get", "/release-package", None),
        ("post", "/release", {"verdict": "blocked"}),
        ("post", "/notify", None),
        ("get", "/knowledge", None),
        ("get", "/regression-set", None),
        ("post", "/defects/999/sync", None),
    ],
)
def test_api_task_routes_hide_cross_project_resources(
    client, auth_headers, db_session, method, suffix, body,
):
    from app.models.version_task_plan import VersionTaskPlanItem
    from app.models.version_task_run import VersionTaskRun

    task = version_task_service.create_task(
        db_session, project_id=13, title="project 13 only", version="1.0"
    )
    item = VersionTaskPlanItem(task_id=task.id, title="private item", status="draft")
    run = VersionTaskRun(
        task_id=task.id, status="blocked", total=1, blocked=1,
        failures='[{"kind":"plan","message":"private"}]',
    )
    db_session.add_all([item, run])
    db_session.commit()

    url = f"/api/v1/version-tasks/{task.id}{suffix}"
    url = url.format(item_id=item.id, run_id=run.id)
    request_kwargs = {"headers": auth_headers}
    if body is not None:
        request_kwargs["json"] = body
    response = getattr(client, method)(url, **request_kwargs)

    assert response.status_code == 404, response.text
    assert response.json()["code"] == 404, response.text
    db_session.refresh(task)
    db_session.refresh(item)
    assert task.title == "project 13 only"
    assert item.status == "draft"

