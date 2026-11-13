"""M10-347b：playwright / appium 执行器测试（mock 浏览器/设备，真实逻辑由本地实测覆盖）。"""
from __future__ import annotations

import sys
import types

import httpx

from app.aiqe.services import node_executor


class _Resp:
    def __init__(self, data):
        self._data = data
        self.status_code = 200

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class _FakeAppiumClient:
    def __init__(self, *args, **kwargs):
        self.calls: list[tuple[str, str]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, path, json=None):
        self.calls.append(("POST", path))
        if path == "/session":
            return _Resp({"value": {"sessionId": "s-1"}})
        if path.endswith("/element"):
            return _Resp({"value": {"ELEMENT": "e-1"}})
        return _Resp({"value": None})

    def get(self, path):
        self.calls.append(("GET", path))
        return _Resp({"value": '<hierarchy><node text="CAMEL LIVE" /></hierarchy>'})

    def delete(self, path):
        self.calls.append(("DELETE", path))
        return _Resp({"value": None})


def test_playwright_is_dispatched(monkeypatch):
    monkeypatch.setattr(
        node_executor,
        "_execute_playwright",
        lambda spec: node_executor.NodeExecution(status="PASSED", detail={"url": "x"}),
    )
    node = types.SimpleNamespace(driver_key="playwright", input_ref={"url": "https://example"})
    assert node_executor.execute_node(node).status == "PASSED"


def test_playwright_missing_browser_blocks(monkeypatch):
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    out = node_executor._execute_playwright({"url": "https://example.com"})
    assert out.status == "BLOCKED"
    assert out.error_class == "BROWSER_UNAVAILABLE"


def test_playwright_requires_url():
    out = node_executor._execute_playwright({})
    assert out.status == "FAILED"
    assert out.error_class == "INPUT_INVALID"


def test_appium_dispatched_and_passes(monkeypatch):
    monkeypatch.setattr(httpx, "Client", _FakeAppiumClient)
    out = node_executor._execute_appium(
        {
            "appium_url": "http://127.0.0.1:4723",
            "app_package": "com.camelrn",
            "expect_text": "CAMEL",
            "click_text": "CAMEL",
        }
    )
    assert out.status == "PASSED", out
    assert out.detail["clicked"] is True
    assert out.detail["expect_text_found"] is True
    assert out.detail["source_len"] > 0


def test_appium_text_mismatch_fails(monkeypatch):
    monkeypatch.setattr(httpx, "Client", _FakeAppiumClient)
    out = node_executor._execute_appium(
        {"appium_url": "http://127.0.0.1:4723", "expect_text": "NOT-THERE"}
    )
    assert out.status == "FAILED"
    assert out.error_class == "TEXT_MISMATCH"


def test_appium_unavailable_blocks(monkeypatch):
    class _Refuse(_FakeAppiumClient):
        def post(self, path, json=None):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "Client", _Refuse)
    out = node_executor._execute_appium({"appium_url": "http://127.0.0.1:9"})
    assert out.status == "BLOCKED"
    assert out.error_class == "APPIUM_UNAVAILABLE"


def test_unknown_driver_blocked():
    node = types.SimpleNamespace(driver_key="iot", input_ref={})
    out = node_executor.execute_node(node)
    assert out.status == "BLOCKED"
    assert out.error_class == "UNSUPPORTED_DRIVER"
