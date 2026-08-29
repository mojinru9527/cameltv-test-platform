"""ShadowAudit feedback tests (V31-015)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.execution import service, shadow_audit
from app.modules.aitde.environment import snapshot_service


def _make_run(db, scenario_graph):
    snap = snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=scenario_graph["mission"].id, project_id=1,
        data={"build_label": "v3.1"},
    )
    return service.create_run(
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


def test_submit_feedback_does_not_change_outcome(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    shadow_audit.submit_feedback(
        db, run.id, 1, "FALSE_PASS", "证据不足但显示 PASS", user_id=5
    )
    # the stored run outcome is untouched (still None / independent)
    row = service.get_run(db, run.id, 1)
    assert row.outcome is None
    feedback = shadow_audit.list_feedback(db, run.id, 1)
    assert len(feedback) == 1
    assert feedback[0].audit_outcome == "FALSE_PASS"


def test_rejects_invalid_audit_outcome(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    with pytest.raises(APIException) as exc:
        shadow_audit.submit_feedback(db, run.id, 1, "MAYBE", "", user_id=5)
    assert exc.value.http_status == 400


def test_audit_scoped_to_project(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    with pytest.raises(APIException) as exc:
        shadow_audit.list_feedback(db, run.id, 2)
    assert exc.value.http_status == 404
