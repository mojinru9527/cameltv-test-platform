"""V3.9-R4 REG-001 — ChangeProvider Registry + source-aware detect.

Verifies the automatic Smart Regression path loads real snapshots through the
ChangeProvider registry (never trusting a caller-supplied baseline/current),
while MANUAL caller payload stays available as a debug path. An unresolvable
source ref must fail closed (no vacuous "no change"), not produce an empty diff.
"""
from __future__ import annotations

import json

import pytest

from app.modules.aitde.mission.models import Mission
from app.modules.aitde.smart_regression import service
from app.modules.aitde.smart_regression.providers import change_provider_registry


def _seed_mission(db) -> int:
    db.add(Mission(id=7, project_id=1, mission_key="m", title="M"))
    db.commit()
    return 7


_BASELINE = {"GET /memberships": {"request_required": [], "responses": {}}}
_CURRENT = {"GET /memberships": {"request_required": ["status"], "responses": {}}}


def _inline(payload: dict) -> str:
    return "inline:" + json.dumps(payload)


def test_provider_mode_loads_via_registry_and_diffs(db):
    mission_id = _seed_mission(db)
    result = service.ChangeSetService.detect(
        db, 1, mission_id, "OPENAPI",
        baseline={}, current={},
        source_from_ref=_inline(_BASELINE), source_to_ref=_inline(_CURRENT),
        source_type="PROVIDER",
    )
    # Real provider loaded its own snapshots from the refs and found a breaking
    # request-required change (CONTRACT_RULE), never a vacuous empty diff.
    assert result["items"]
    changed = [i for i in result["items"] if i["change_kind"] == "CHANGED"]
    assert any(i["risk_hint"] == "CONTRACT_RULE" for i in changed)
    # provenance recorded
    assert result["source_from_ref"].startswith("inline:")
    assert result["source_to_ref"].startswith("inline:")


def test_manual_mode_uses_caller_payload(db):
    mission_id = _seed_mission(db)
    result = service.ChangeSetService.detect(
        db, 1, mission_id, "OPENAPI",
        baseline=_BASELINE, current=_CURRENT,
        source_type="MANUAL",
    )
    assert result["items"]


def test_provider_unresolvable_ref_fails_closed(db):
    mission_id = _seed_mission(db)
    # A ref that is not a resolvable snapshot must not silently produce "no change".
    with pytest.raises(ValueError):
        service.ChangeSetService.detect(
            db, 1, mission_id, "OPENAPI",
            baseline=None, current=None,
            source_from_ref="environment:999", source_to_ref="environment:1000",
            source_type="PROVIDER",
        )


def test_registry_has_openapi_and_db_schema_providers():
    assert change_provider_registry.get("OPENAPI") is not None
    assert change_provider_registry.get("DB_SCHEMA") is not None
    assert change_provider_registry.get("UNKNOWN") is None
