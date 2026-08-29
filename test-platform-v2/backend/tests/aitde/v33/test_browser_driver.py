"""V33-004 BrowserRuntimeDriver tests (fake adapter — no live Chromium).

Verifies the driver's command-dispatch, semantic locator resolution (plan §4
priority order), replay evidence capture, and the AUTOMATION_FAIL mapping — all
without launching a real browser.
"""

from __future__ import annotations

from app.modules.aitde.browser.driver import BrowserRuntimeDriver, resolve_locator
from app.modules.aitde.browser.driver import BrowserRuntimeError


class FakeAdapter:
    """Records §4 unified-method calls and returns canned evidence."""

    def __init__(self):
        self.calls: list[tuple] = []
        self.opened = False
        self.closed = False
        self.content_html = "<html><body>ok</body></html>"

    def open(self):
        self.opened = True
        self.calls.append(("open",))

    def goto(self, route):
        self.calls.append(("goto", route))
        return f"https://app.example{route}"

    def click(self, locator):
        self.calls.append(("click", locator))

    def fill(self, locator, value):
        self.calls.append(("fill", locator, value))

    def select(self, locator, value):
        self.calls.append(("select", locator, value))

    def upload(self, locator, file):
        self.calls.append(("upload", locator, file))

    def wait_for(self, locator):
        self.calls.append(("wait_for", locator))

    def content(self):
        return self.content_html

    def screenshot(self):
        return b"\x89PNGfake"

    def network_events(self):
        return [{"kind": "request", "url": "https://x", "method": "GET"}]

    def trace_path(self):
        return None

    def close(self):
        self.closed = True
        self.calls.append(("close",))


def _ir(commands):
    return {"schema_version": "1.0", "commands": commands}


# ── locator resolution (plan §4 priority) ──
def test_resolve_data_testid():
    r = resolve_locator({"data-testid": "renew", "role": "button"})
    assert r["kind"] == "data-testid"
    assert r["selector"] == "renew"


def test_resolve_role_with_name():
    r = resolve_locator({"role": "button", "name": "立即续费"})
    assert r["kind"] == "role"
    assert r["role"] == "button"
    assert r["name"] == "立即续费"


def test_resolve_role_bare():
    r = resolve_locator({"role": "button"})
    assert r["kind"] == "role"
    assert r["role"] == "button"
    assert "name" not in r


def test_resolve_label_and_text():
    assert resolve_locator({"label": "用户名"}) == {
        "kind": "label",
        "selector": "用户名",
    }
    assert resolve_locator({"text": "续费"}) == {"kind": "text", "selector": "续费"}


def test_resolve_css_last_resort():
    assert resolve_locator({"strategy": "css", "selector": "#btn"}) == {
        "kind": "css",
        "selector": "#btn",
    }
    assert resolve_locator({}) == {"kind": "css", "selector": ""}


# ── command dispatch ──
def test_executes_browser_plan_in_order():
    adapter = FakeAdapter()
    driver = BrowserRuntimeDriver(adapter=adapter)
    result = driver.execute(
        _ir(
            [
                {
                    "id": "1",
                    "driver": "browser",
                    "action": "open_session",
                    "input": {"mode": "REGRESSION"},
                },
                {
                    "id": "2",
                    "driver": "browser",
                    "action": "goto",
                    "input": {"route": "/member"},
                },
                {
                    "id": "3",
                    "driver": "browser",
                    "action": "click",
                    "input": {"locator": {"role": "button", "name": "立即续费"}},
                },
            ]
        )
    )
    assert result["status"] == "success"
    # open() then goto then click
    assert adapter.calls[0] == ("open",)
    assert adapter.calls[1] == ("goto", "/member")
    assert adapter.calls[2] == (
        "click",
        {
            "kind": "role",
            "role": "button",
            "name": "立即续费",
            "selector": 'role=button[name="立即续费"]',
        },
    )
    assert [c["status"] for c in result["commands"]] == ["ok", "ok", "ok"]


def test_skips_non_browser_driver():
    adapter = FakeAdapter()
    driver = BrowserRuntimeDriver(adapter=adapter)
    result = driver.execute(
        _ir(
            [
                {
                    "id": "1",
                    "driver": "data",
                    "action": "ensure",
                    "input": {"requirement_ref": "x"},
                },
                {
                    "id": "2",
                    "driver": "browser",
                    "action": "open_session",
                    "input": {"mode": "REGRESSION"},
                },
            ]
        )
    )
    assert result["status"] == "success"
    assert result["commands"][0]["status"] == "skipped"
    assert adapter.opened is True


# ── evidence capture ──
def test_captures_dom_screenshot_network_evidence():
    adapter = FakeAdapter()
    driver = BrowserRuntimeDriver(adapter=adapter)
    result = driver.execute(
        _ir(
            [
                {
                    "id": "1",
                    "driver": "browser",
                    "action": "open_session",
                    "input": {"mode": "REGRESSION"},
                },
                {"id": "2", "driver": "browser", "action": "capture_dom"},
                {"id": "3", "driver": "browser", "action": "capture_screenshot"},
                {"id": "4", "driver": "browser", "action": "capture_network"},
            ]
        )
    )
    kinds = {e["type"] for e in result["evidence"]}
    assert kinds == {"dom", "screenshot", "network"}
    assert any(
        e["type"] == "dom" and e["html"] == "<html><body>ok</body></html>"
        for e in result["evidence"]
    )
    assert any(e["type"] == "screenshot" and e["bytes"] > 0 for e in result["evidence"])
    assert any(e["type"] == "network" and e["events"] for e in result["evidence"])


# ── runtime failure → AUTOMATION_FAIL (never BUSINESS_FAIL) ──
def test_runtime_error_maps_to_runtime_error_not_business_fail():
    class BrokenAdapter(FakeAdapter):
        def click(self, locator):
            raise BrowserRuntimeError("element not found")

    driver = BrowserRuntimeDriver(adapter=BrokenAdapter())
    result = driver.execute(
        _ir(
            [
                {
                    "id": "1",
                    "driver": "browser",
                    "action": "open_session",
                    "input": {"mode": "REGRESSION"},
                },
                {
                    "id": "2",
                    "driver": "browser",
                    "action": "click",
                    "input": {"locator": {"role": "button", "name": "x"}},
                },
            ]
        )
    )
    # runtime/environment problem must not be reported as a business pass/fail
    assert result["status"] == "runtime_error"
    assert "element not found" in result["commands"][-1]["reason"]
    # opened session is cleaned up on error
    assert result["commands"][0]["status"] == "ok"


def test_ir_not_object():
    driver = BrowserRuntimeDriver(adapter=FakeAdapter())
    result = driver.execute("nonsense")
    assert result["status"] == "runtime_error"


def test_unknown_browser_action_rejected():
    driver = BrowserRuntimeDriver(adapter=FakeAdapter())
    result = driver.execute(_ir([{"driver": "browser", "action": "not_real"}]))
    # An action outside the registry is rejected deterministically (unknown-command
    # reject per V33-001) and surfaces as runtime_error, never executing adapter.
    assert result["status"] == "runtime_error"
    assert "unknown browser action" in result["commands"][-1]["reason"]
