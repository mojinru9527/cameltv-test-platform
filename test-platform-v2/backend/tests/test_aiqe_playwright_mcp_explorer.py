"""M3 / TA-016：Playwright MCP Explorer 单测（fake driver）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EXPLORER_PATH = (
    ROOT / "scripts" / "node" / "cameltv_node" / "mcp" / "playwright_mcp" / "explorer.py"
)


def load_explorer():
    spec = importlib.util.spec_from_file_location("pw_explorer_under_test", EXPLORER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeDriver:
    def __init__(self, tmp_path: Path) -> None:
        self.calls: list[tuple] = []
        self.tmp_path = tmp_path
        self.fail_on: str | None = None

    def goto(self, url):
        self.calls.append(("goto", url))

    def click(self, selector):
        if self.fail_on == "click":
            raise RuntimeError("click failed")
        self.calls.append(("click", selector))

    def fill(self, selector, value):
        self.calls.append(("fill", selector, value))

    def wait_for(self, selector):
        self.calls.append(("wait_for", selector))

    def text(self, selector):
        self.calls.append(("text", selector))
        return "hello"

    def capture_evidence(self):
        dom = self.tmp_path / "dom.html"
        a11y = self.tmp_path / "a11y.json"
        dom.write_text("<html>explored</html>", encoding="utf-8")
        a11y.write_text('{"role": "main"}', encoding="utf-8")
        return [
            {"name": "dom.html", "type": "dom", "path": str(dom), "size_bytes": dom.stat().st_size},
            {"name": "a11y.json", "type": "a11y", "path": str(a11y), "size_bytes": a11y.stat().st_size},
        ]


@pytest.fixture()
def explorer_module():
    return load_explorer()


def test_explore_allowed_domain(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    explorer = explorer_module.PlaywrightExplorer(
        allowed_domains=["admin.test"], driver=driver
    )
    result = explorer.explore(
        "https://admin.test/live",
        [{"action": "click", "selector": "#publish"}],
    )
    assert result["ok"] is True
    assert result["dom"] == "<html>explored</html>"
    assert result["a11y"] == '{"role": "main"}'
    assert [a["action"] for a in result["actions"]] == ["goto", "click"]
    assert driver.calls == [("goto", "https://admin.test/live"), ("click", "#publish")]


def test_disallowed_domain_rejected_before_navigation(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    explorer = explorer_module.PlaywrightExplorer(allowed_domains=["admin.test"], driver=driver)
    with pytest.raises(explorer_module.DomainNotAllowed):
        explorer.explore("https://evil.test/steal")
    assert driver.calls == []


def test_wildcard_subdomain_allowed(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    explorer = explorer_module.PlaywrightExplorer(allowed_domains=["*.example.com"], driver=driver)
    assert explorer.explore("https://api.example.com/x")["ok"] is True
    with pytest.raises(explorer_module.DomainNotAllowed):
        explorer.explore("https://example.com.evil.test/")


def test_non_http_scheme_rejected(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    explorer = explorer_module.PlaywrightExplorer(allowed_domains=["admin.test"], driver=driver)
    with pytest.raises(explorer_module.DomainNotAllowed):
        explorer.explore("file:///etc/passwd")


def test_action_failure_stops_and_logs(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    driver.fail_on = "click"
    explorer = explorer_module.PlaywrightExplorer(allowed_domains=["admin.test"], driver=driver)
    result = explorer.explore(
        "https://admin.test/x",
        [{"action": "click", "selector": "#a"}, {"action": "click", "selector": "#b"}],
    )
    assert result["ok"] is False
    assert "click failed" in result["error"]
    assert [a["ok"] for a in result["actions"]] == [True, False]
    assert len(result["actions"]) == 2


def test_unknown_action_logged(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    explorer = explorer_module.PlaywrightExplorer(allowed_domains=["admin.test"], driver=driver)
    result = explorer.explore("https://admin.test/x", [{"action": "hack", "selector": "#a"}])
    assert result["ok"] is False
    assert "未知动作" in result["error"]


def test_metadata_ip_rejected(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    explorer = explorer_module.PlaywrightExplorer(allowed_domains=["admin.test"], driver=driver)
    with pytest.raises(explorer_module.DomainNotAllowed):
        explorer.explore("http://169.254.169.254/latest/meta-data")


def test_handle_tool_explore_page(explorer_module, tmp_path):
    driver = FakeDriver(tmp_path)
    explorer = explorer_module.PlaywrightExplorer(allowed_domains=["admin.test"], driver=driver)
    result = explorer_module.handle_tool(
        "explore_page",
        {"url": "https://admin.test/x", "actions": [{"action": "text", "selector": "#t"}]},
        explorer=explorer,
    )
    assert result["ok"] is True
    with pytest.raises(explorer_module.ExplorerError):
        explorer_module.handle_tool("unknown", {}, explorer=explorer)
