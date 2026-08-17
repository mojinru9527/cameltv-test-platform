"""knowledge-mcp 工具层单测 — DSH 测试 Agent 框架（阶段 1）。

验证工具函数经 _call 组装正确的 open API 路径/方法/参数/鉴权头。
（不实际连平台；_call 打桩。）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PLATFORM_BASE_URL", "http://platform.test:8055")
    monkeypatch.setenv("PLATFORM_API_TOKEN", "tpat_unit")
    monkeypatch.setenv("PLATFORM_PROJECT_ID", "7")
    # 模块加载后重读配置
    kms.BASE_URL = "http://platform.test:8055"
    kms.API_TOKEN = "tpat_unit"
    kms.PROJECT_ID = "7"
    yield


def _capture(monkeypatch):
    """打桩 _call，记录调用参数。"""
    calls = []

    def fake_call(method, path, json_body=None, params=None):
        calls.append({"method": method, "path": path, "json": json_body, "params": params})
        return {"ok": True}

    monkeypatch.setattr(kms, "_call", fake_call)
    return calls


# ── 查询面 ──

def test_search_knowledge(monkeypatch):
    calls = _capture(monkeypatch)
    kms.search_knowledge("登录", top_k=5)
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/knowledge/search"
    assert calls[0]["json"] == {"query": "登录", "top_k": 5}


def test_get_module_topology(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_module_topology()
    assert calls[0]["path"] == "/knowledge/modules"
    assert calls[0]["params"] is None

    calls.clear()
    kms.get_module_topology("支付")
    assert calls[0]["params"] == {"module": "支付"}


def test_get_knowledge_sources(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_knowledge_sources(source_type="requirement", keyword="登录")
    assert calls[0]["path"] == "/knowledge/sources"
    assert calls[0]["params"] == {"source_type": "requirement", "keyword": "登录"}


def test_get_requirements(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_requirements()
    assert calls[0]["path"] == "/requirements"
    assert calls[0]["params"] is None


def test_get_test_cases(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_test_cases(module="登录", priority="P1")
    assert calls[0]["path"] == "/test-cases"
    assert calls[0]["params"] == {"module": "登录", "priority": "P1"}


# ── 执行面 ──

def test_get_test_plans(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_test_plans(status="active", keyword="登录")
    assert calls[0]["path"] == "/plans"
    assert calls[0]["params"] == {"status": "active", "keyword": "登录"}


def test_get_test_plan(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_test_plan(42)
    assert calls[0]["path"] == "/plans/42"


def test_get_plan_executions(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_plan_executions(42, page_size=20)
    assert calls[0]["path"] == "/plans/42/executions"
    assert calls[0]["params"] == {"page_size": 20}


def test_trigger_test_plan(monkeypatch):
    calls = _capture(monkeypatch)
    kms.trigger_test_plan(42)
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/plans/42/trigger"


def test_get_execution_result(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_execution_result(99)
    assert calls[0]["method"] == "GET"
    assert calls[0]["path"] == "/runs/99"


# ── UI 自动化面（阶段 3）──

def test_get_ui_test_jobs(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_ui_test_jobs()
    assert calls[0]["path"] == "/ui-tests"
    assert calls[0]["params"] is None

    calls.clear()
    kms.get_ui_test_jobs("登录")
    assert calls[0]["params"] == {"keyword": "登录"}


def test_trigger_ui_test(monkeypatch):
    calls = _capture(monkeypatch)
    kms.trigger_ui_test(7)
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/ui-tests/7/trigger"


def test_get_ui_test_run(monkeypatch):
    calls = _capture(monkeypatch)
    kms.get_ui_test_run(88)
    assert calls[0]["method"] == "GET"
    assert calls[0]["path"] == "/ui-tests/runs/88"


# ── 回写面 ──

def test_submit_test_cases(monkeypatch):
    calls = _capture(monkeypatch)
    kms.submit_test_cases([
        {"title": "用例1", "module": "登录"},
        {"title": "用例2"},
    ])
    assert len(calls) == 2
    assert all(c["method"] == "POST" and c["path"] == "/test-cases" for c in calls)
    assert calls[0]["json"] == {"title": "用例1", "module": "登录"}


# ── 鉴权头/URL 组装（真实 _call，httpx 打桩）──

def test_call_builds_auth_headers(monkeypatch):
    sent = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"code": 0, "msg": "ok", "data": {"x": 1}}

    def fake_get(url, headers=None, params=None, timeout=None):
        sent["url"] = url
        sent["headers"] = headers
        sent["params"] = params
        return FakeResponse()

    monkeypatch.setattr(kms.httpx, "get", fake_get)
    data = kms._call("GET", "/knowledge/modules", params={"module": "登录"})
    assert data == {"x": 1}
    assert sent["url"] == "http://platform.test:8055/api/v1/open/knowledge/modules"
    assert sent["headers"]["Authorization"] == "Bearer tpat_unit"
    assert sent["headers"]["X-Project-Id"] == "7"
    assert sent["params"] == {"module": "登录"}


def test_call_raises_on_business_error(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"code": 403, "msg": "无权限"}

    monkeypatch.setattr(kms.httpx, "get", lambda *a, **kw: FakeResponse())
    with pytest.raises(RuntimeError, match="业务错误"):
        kms._call("GET", "/knowledge/modules")
