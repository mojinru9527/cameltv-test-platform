"""Batch 266 / C264-3 + C264-4 — 执行链路可执行性与用例隔离。

覆盖三处修复：
  1. 断言支持 `status_code` + `operator`（gte/lt/eq…），未知算子仍失败；
  2. `expect_visible` 改为"任一匹配可见"，与 `wait_visible` 语义一致；
  3. Web 用例**每条独立浏览器上下文**（此前共用一个，站点状态串味）。
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

NODE_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "node"
if str(NODE_ROOT) not in sys.path:
    sys.path.insert(0, str(NODE_ROOT))

from cameltv_node import executor as node_executor  # noqa: E402


class _Locator:
    def __init__(self, visibility: list[bool]):
        self._visibility = visibility

    def count(self) -> int:
        return len(self._visibility)

    def nth(self, index: int):
        outer = self

        class _Element:
            def is_visible(self) -> bool:
                return outer._visibility[index]

        return _Element()


class _Page:
    def __init__(self, visibility: list[bool]):
        self._visibility = visibility

    def locator(self, selector: str) -> _Locator:
        return _Locator(self._visibility)

    def is_visible(self, selector: str) -> bool:  # 仅首个匹配（旧语义）
        return bool(self._visibility and self._visibility[0])


class _LegacyPage:
    """不实现 locator 的替身（验证回退路径）。"""

    def is_visible(self, selector: str) -> bool:
        return True


def test_status_code_operator_gte_and_lt_support_range():
    assertions = [
        {"type": "status_code", "expected": 200, "operator": "gte"},
        {"type": "status_code", "expected": 300, "operator": "lt"},
    ]
    results = node_executor.evaluate_assertions(
        status_code=204, text="", payload={}, assertions=assertions
    )
    assert [item["passed"] for item in results] == [True, True]


def test_status_code_operator_eq_and_unknown_operator():
    eq = node_executor.evaluate_assertions(
        status_code=200, text="", payload={}, assertions=[{"type": "status_code", "expected": 200, "operator": "eq"}]
    )
    assert eq[0]["passed"] is True

    unknown = node_executor.evaluate_assertions(
        status_code=200, text="", payload={}, assertions=[{"type": "status_code", "expected": 200, "operator": "between"}]
    )
    assert unknown[0]["passed"] is False
    assert "未识别的断言算子" in str(unknown[0]["actual"])


def test_status_code_range_outside_bounds_fails():
    results = node_executor.evaluate_assertions(
        status_code=500, text="", payload={}, assertions=[{"type": "status_code", "expected": 300, "operator": "lt"}]
    )
    assert results[0]["passed"] is False


def test_lowercase_jsonpath_alias_and_none_expected_means_existence():
    payload = {"status": 200, "data": {"id": 7}}
    results = node_executor.evaluate_assertions(
        status_code=200,
        text="",
        payload=payload,
        assertions=[
            {"type": "jsonpath", "path": "$.status", "expected": 200},
            {"type": "jsonpath", "path": "$.data.id", "expected": None},
            {"type": "jsonpath", "path": "$.data.missing", "expected": None},
        ],
    )
    assert [item["passed"] for item in results] == [True, True, False]


def test_response_time_assertion_uses_elapsed_ms():
    ok = node_executor.evaluate_assertions(
        status_code=200, text="", payload={}, assertions=[{"type": "response_time", "expected": 5000}], elapsed_ms=123.4
    )
    assert ok[0]["passed"] is True

    slow = node_executor.evaluate_assertions(
        status_code=200, text="", payload={}, assertions=[{"type": "response_time", "expected": 100}], elapsed_ms=250.0
    )
    assert slow[0]["passed"] is False

    unknown = node_executor.evaluate_assertions(
        status_code=200, text="", payload={}, assertions=[{"type": "response_time", "expected": 100}], elapsed_ms=None
    )
    assert unknown[0]["passed"] is False


def test_any_visible_uses_any_match_not_only_first():
    page = _Page([False, True])
    assert node_executor._any_visible(page, "text=News") is True
    assert _Page([False, False]).locator("x").count() == 2
    assert node_executor._any_visible(_Page([False, False]), "text=News") is False


def test_any_visible_falls_back_for_objects_without_locator():
    assert node_executor._any_visible(_LegacyPage(), "text=News") is True


def test_web_cases_get_fresh_context_per_case(tmp_path):
    """每条用例都应新建上下文（工厂被调用 N 次），避免站点状态串味。"""
    calls = {"count": 0}

    class _CasePage:
        def goto(self, url, **kwargs):
            return None

        def is_visible(self, selector):
            return True

    def _factory():
        calls["count"] += 1
        return contextlib.nullcontext(_CasePage())

    cases = [{"id": f"ui-{i}", "steps": [{"action": "goto", "url": "/"}]} for i in range(3)]
    results = node_executor.run_web_cases(cases, evidence_dir=tmp_path, page_factory=_factory)
    assert results["total"] == 3
    assert calls["count"] == 3


def test_environment_level_unavailable_still_propagates(tmp_path):
    """环境级不可用（未装 Playwright）必须抛出，不能被"用例级异常收敛"吞掉。"""
    import pytest

    def _unavailable():
        raise node_executor.ExecutorUnavailable("未安装 Playwright")

    with pytest.raises(node_executor.ExecutorUnavailable):
        node_executor.run_web_cases(
            [{"id": "ui-x", "steps": [{"action": "goto", "url": "/"}]}],
            evidence_dir=tmp_path,
            page_factory=_unavailable,
        )
