"""V3.9-R2 HYBRID-001 — no runner must not fake ``executed=True``.

A Hybrid run with no Action Runner is a capability failure (AUTOMATION_FAIL /
BLOCKED), never a silent success. ``preflight()`` reports required capabilities.
"""
from __future__ import annotations

from app.modules.aitde.hybrid.coordinator import (
    ACTION_RUNNER_NOT_CONFIGURED,
    HybridExecutionCoordinator,
    RuntimeCapabilityError,
)


def test_preflight_reports_missing_capabilities():
    coord = HybridExecutionCoordinator()
    preflight = coord.preflight()
    assert preflight["ready"] is False
    assert "action_runner" in preflight["missing"]


def test_no_action_runner_never_fakes_executed(db, run_graph):
    coord = HybridExecutionCoordinator()
    dispatch = coord._run_actions_and_oracles(db, run_graph["run"])
    assert dispatch["action"].get("executed") is not True
    assert dispatch["action"]["error"] == ACTION_RUNNER_NOT_CONFIGURED
    assert dispatch["action"]["blocked"] is True
    assert dispatch["action"]["automation_error"] is True


def test_capability_error_carries_stable_code():
    exc = RuntimeCapabilityError(ACTION_RUNNER_NOT_CONFIGURED)
    assert exc.code == ACTION_RUNNER_NOT_CONFIGURED
    assert ACTION_RUNNER_NOT_CONFIGURED in str(exc)
