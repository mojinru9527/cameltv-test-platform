"""Legacy API/UI bridge tests (V31-009/V31-010)."""
from __future__ import annotations

from app.modules.aitde.execution import legacy_bridge, repository
from app.modules.aitde.execution.service import create_run

# Reuse the run-creation helpers so a legacy bridge lands on a real run.


def _make_run(db, scenario_graph):
    from app.modules.aitde.environment import snapshot_service

    snap = snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=scenario_graph["mission"].id, project_id=1,
        data={"build_label": "v3.1"},
    )
    return create_run(
        db,
        {
            "mission_id": scenario_graph["mission"].id,
            "scenario_id": scenario_graph["scenario"].id,
            "scenario_version_id": scenario_graph["scenario_version"].id,
            "contract_version_id": scenario_graph["contract_version"].id,
            "environment_id": 1,
            "environment_snapshot_id": snap.id,
        },
        project_id=1,
        user_id=9,
    )


def test_api_bridge_is_idempotent_and_does_not_hit_legacy(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    legacy_id = 777
    result = legacy_bridge.bridge_api_item(
        db, project_id=1, run_id=run.id, legacy_id=legacy_id,
        request={"url": "https://api.example.com/x"}, response={"code": 0, "data": {}},
    )
    assert result["run_id"] == run.id
    assert len(result["artifacts"]) == 2  # REQUEST + RESPONSE

    # second registration must be a no-op (idempotent link)
    again = legacy_bridge.bridge_api_item(
        db, project_id=1, run_id=run.id, legacy_id=legacy_id,
        request={"url": "x"}, response={"code": 0},
    )
    assert again.get("already_linked") is True
    steps = repository.list_steps(db, run.id, 1)
    assert len(steps) == 1  # only one step created despite two calls


def test_ui_bridge_registers_screenshots_and_video(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    result = legacy_bridge.bridge_ui_run(
        db, project_id=1, run_id=run.id, legacy_id=888,
        screenshots=["/art/shot1.png", "/art/shot2.png"],
        video_url="https://cdn/v.mp4", trace_id="trace-abc",
        result_summary={"pass": 3},
    )
    types = {a["type"] for a in result["artifacts"]}
    assert "SCREENSHOT" in types
    assert "VIDEO" in types
    assert "PW_TRACE" in types
