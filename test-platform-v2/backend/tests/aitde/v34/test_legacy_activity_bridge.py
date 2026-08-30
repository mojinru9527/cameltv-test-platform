"""AITDE V3.4 legacy runner Temporal bridge tests (V34-013 / V34-014).

The API/UI runner Activities wrap the existing legacy execution path and bridge
it into the unified model. Real HTTP/Playwright execution needs infrastructure;
these tests assert (a) the activities are registered on the worker and (b) the
shadow-equivalence / evidence-retention contract via mocked runner + real bridge.
"""
from __future__ import annotations

from app.modules.aitde.workflow import gateway as gw


def test_legacy_bridge_activities_registered():
    names = {a.__name__ for a in gw.get_activities()}
    assert "run_legacy_api_task" in names
    assert "run_legacy_ui_task" in names


def test_cache_is_pure_contract():
    """The activities are async defn wrappers whose bodies resolve the runner +
    bridge at call time (so the Worker can bind them without importing the whole
    legacy chain eagerly)."""
    import inspect

    names = {"run_legacy_api_task", "run_legacy_ui_task"}
    from app.temporal import activities

    for n in names:
        assert inspect.iscoroutinefunction(getattr(activities, n))


# ── shadow-equivalence via the existing legacy bridge (no real network) ───────


def test_api_bridge_shadow_assertions_written(db_with_v34):
    """Bridging a legacy API item writes mapped assertions, so the unified run is
    not evidence-less (V34-013 shadow-equivalence foundation)."""
    from app.modules.aitde.common.enums import LegacyExecutionType
    from app.modules.aitde.execution import legacy_bridge

    result = legacy_bridge.bridge_api_item(
        db_with_v34,
        project_id=1,
        legacy_id=901,
        request={"path": "/health"},
        response={"body": "ok"},
        assertions=[
            {"type": "json", "expected": 200, "actual": 200, "passed": True},
            {"type": "json", "expected": "x", "actual": "y", "passed": False},
        ],
        environment_id=2,
    )
    assert result["run_id"] > 0
    assert len(result["assertions"]) == 2
    statuses = {a["result"] for a in result["assertions"]}
    assert statuses == {"PASS", "FAIL"}
    # Bridge is idempotent (no duplicate on re-link).
    again = legacy_bridge.bridge_api_item(db_with_v34, project_id=1, legacy_id=901)
    assert again.get("already_linked") is True


def test_ui_bridge_evidence_retained(db_with_v34):
    """Bridging a UI run retains screenshot/trace evidence (V34-014)."""
    from app.modules.aitde.execution import legacy_bridge

    result = legacy_bridge.bridge_ui_run(
        db_with_v34,
        project_id=1,
        legacy_id=902,
        screenshots=["shot1.png"],
        video_url="run.webm",
        trace_id="trace.zip",
        console_text="console log",
        environment_id=2,
    )
    assert result["run_id"] > 0
    types = {a["type"] for a in result["artifacts"]}
    assert {"SCREENSHOT", "VIDEO", "PW_TRACE", "CONSOLE"} <= types
