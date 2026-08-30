"""AITDE V3.4/V3.5 real API driver tests (execute_commands / evaluate_oracles hooks).

Deterministic, CI-safe (no live network): verifies the drivers register the real
hooks and that the deterministic helpers (JSONPath + compare) used by the driver
resolve nested/array paths and evaluate real assertions correctly.
"""
from __future__ import annotations

from app.modules.aitde.workflow import drivers
from app.temporal import activities


def test_api_driver_hooks_registered():
    # Importing this module registers the real driver hooks (V34-004 extension).
    assert "resolve_command_plan" in activities._EXEC_HOOKS
    assert "execute_commands" in activities._EXEC_HOOKS
    assert "evaluate_oracles" in activities._EXEC_HOOKS


def test_json_path_resolves_nested_and_array():
    data = {
        "traceId": "abc",
        "data": {"result": {"Hot": [{"id": "z1", "name": "UEFA Champions League"}, {"id": "z2", "name": "NBA"}]}},
    }
    assert drivers._json_path(data, "data.result.Hot") == data["data"]["result"]["Hot"]
    assert drivers._json_path(data, "data.result.Hot[0].name") == "UEFA Champions League"
    assert drivers._json_path(data, "data.result.Hot[1].name") == "NBA"
    assert drivers._json_path(data, "data.result.Missing") is None
    assert drivers._json_path(data, "data.result.Hot[9].name") is None


def test_compare_actual():
    assert drivers._compare_actual(200, "equals", 200) is True
    assert drivers._compare_actual(200, "equals", 201) is False
    assert drivers._compare_actual([1, 2], "exists", True) is True
    assert drivers._compare_actual(None, "exists", True) is False
    assert drivers._compare_actual("UEFA Champions League", "contains", "Champions") is True
    assert drivers._compare_actual(3, "gt", 2) is True
