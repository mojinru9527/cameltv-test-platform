"""CERT-006 — Smart Regression synthetic golden (diff → change-set → impact).

A minimal, deterministic golden for the smart-regression chain: a baseline and a
current OpenAPI snapshot are diffed by the real ``ChangeSetService.detect``
(OpenAPI provider), and we assert the detected change items match the golden
expectation. This is the runnable baseline a tester/human can review for
"which change happened and what it means" (CERT-006).
"""
from __future__ import annotations

from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import (
    TestScenario as ScenarioModel,
    TestScenarioVersion as ScenarioVersionModel,
)
from app.modules.aitde.smart_regression import service


def _setup(db) -> int:
    m = Mission(project_id=1, mission_key="golden", title="CERT-006 golden")
    db.add(m)
    db.flush()
    sc = ScenarioModel(project_id=1, mission_id=m.id, scenario_key="sc-renew")
    db.add(sc)
    db.flush()
    db.add(
        ScenarioVersionModel(
            id=None, scenario_id=sc.id, version_no=1, contract_version_id=100,
            risk_level="P0", title="renew",
        )
    )
    db.commit()
    return m.id


# Baseline / current OpenAPI snapshots (the golden input). Adding a required
# request param is a breaking CONTRACT_RULE change.
BASELINE = {"GET /memberships": {"request_required": [], "responses": {}}}
CURRENT = {"GET /memberships": {"request_required": ["status"], "responses": {}}}


def test_cert006_openapi_diff_golden(db):
    mission_id = _setup(db)
    result = service.ChangeSetService.detect(
        db, 1, mission_id, "OPENAPI", BASELINE, CURRENT, source_type="MANUAL"
    )
    items = result["items"]
    assert items, "golden must produce a change item"
    changed = [i for i in items if i["change_kind"] == "CHANGED"]
    assert changed, "expected a CHANGED item"
    assert any(i["risk_hint"] == "CONTRACT_RULE" for i in changed)
    assert changed[0]["entity_key"] == "GET /memberships"
    # No spurious ADDED / DELETED items.
    assert not any(i["change_kind"] == "ADDED" for i in items)
    # The change set is persisted and re-detectable (idempotent hash).
    again = service.ChangeSetService.detect(
        db, 1, mission_id, "OPENAPI", BASELINE, CURRENT, source_type="MANUAL"
    )
    assert again["id"] == result["id"]
