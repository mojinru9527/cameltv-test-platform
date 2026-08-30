"""AITDE V3.7 impact / regression selector / coverage guard / campaign tests."""

from __future__ import annotations

from app.modules.aitde.common.enums import (
    RiskHint,
    RiskLevel,
    SelectionType,
)
from app.modules.aitde.continuous.models import CampaignScenario, ExecutionCampaign
from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion
from app.modules.aitde.smart_regression import service


def _mission(db, project_id=1, mission_id=7):
    """Create three scenarios: SC1(P0), SC2(P2), SC3(P3)."""
    rows = []
    for key, risk in (
        ("SC1", RiskLevel.P0.value),
        ("SC2", RiskLevel.P2.value),
        ("SC3", RiskLevel.P3.value),
    ):
        sc = TestScenario(
            project_id=project_id, mission_id=mission_id, scenario_key=key
        )
        db.add(sc)
        db.flush()
        db.add(
            TestScenarioVersion(
                scenario_id=sc.id, version_no=1, risk_level=risk, contract_version_id=0
            )
        )
        db.flush()
        rows.append(sc)
    return rows


def test_detect_reuses_same_hash_changeset(db):
    signals = [{"scenario_id": 2, "risk_hint": RiskHint.LAST_BUSINESS_FAIL.value}]
    cs1 = service.detect_risk_signals(db, 7, signals)
    cs2 = service.detect_risk_signals(db, 7, signals)
    assert cs1["id"] == cs2["id"]  # same content_hash -> deduped
    assert cs1["change_type"] == "HISTORICAL_RISK"


def test_impact_and_selection_include_p0(db):
    _mission(db)
    signals = [
        {
            "scenario_id": 2,
            "risk_hint": RiskHint.LAST_BUSINESS_FAIL.value,
            "reason": "run 9 fail",
        }
    ]
    cs = service.detect_risk_signals(db, 7, signals)
    run = service.ImpactAnalyzer.analyze(db, 1, 7, cs["id"], "v1")
    assert run["status"] == "COMPLETED"
    assert run["finished_at"] is not None
    scenario_ids = {r["scenario_id"] for r in run["results"]}
    assert 2 in scenario_ids  # SC2 impacted

    selection = service.RegressionSelector.select(db, 1, 7, run["id"])
    selected_ids = {s["scenario_id"] for s in selection["selected"]}
    assert selection["selection_type"] == SelectionType.SMART.value
    # P0 (SC1) is mandatory include even though not impacted; SC2 impacted.
    assert 1 in selected_ids and 2 in selected_ids
    assert 3 not in selected_ids  # SC3 not impacted, not P0 -> excluded
    excluded_ids = {s["scenario_id"] for s in selection["excluded"]}
    assert 3 in excluded_ids


def test_p0_never_excluded(db):
    _mission(db)
    # No signals at all -> no impacted scenarios, but P0 must still be selected.
    cs = service.detect_risk_signals(db, 7, [])
    run = service.ImpactAnalyzer.analyze(db, 1, 7, cs["id"], "v1")
    selection = service.RegressionSelector.select(db, 1, 7, run["id"])
    selected_ids = {s["scenario_id"] for s in selection["selected"]}
    assert 1 in selected_ids
    assert "mandatory P0 include" in next(
        s["reason"] for s in selection["selected"] if s["scenario_id"] == 1
    )


def test_coverage_guard_fallback_empty_and_unknown(db):
    _mission(db)
    cs = service.detect_risk_signals(
        db, 7, [{"scenario_id": 2, "risk_hint": RiskHint.LAST_BUSINESS_FAIL.value}]
    )
    run = service.ImpactAnalyzer.analyze(db, 1, 7, cs["id"], "v1")
    selection = service.RegressionSelector.select(db, 1, 7, run["id"])
    guard_ok = service.CoverageGuard.guard(db, 1, 7, selection["id"], [])
    assert guard_ok["ok"] is True
    guard_fb = service.CoverageGuard.guard(
        db, 1, 7, selection["id"], [{"entity_type": "API_ENDPOINT", "entity_key": "x"}]
    )
    assert guard_fb["ok"] is False
    assert guard_fb["fallback_to"] == SelectionType.FULL.value


def test_campaign_factory_creates_campaign(db):
    _mission(db)
    cs = service.detect_risk_signals(
        db, 7, [{"scenario_id": 2, "risk_hint": RiskHint.LAST_BUSINESS_FAIL.value}]
    )
    run = service.ImpactAnalyzer.analyze(db, 1, 7, cs["id"], "v1")
    selection = service.RegressionSelector.select(db, 1, 7, run["id"])
    campaign = service.SmartRegressionCampaignFactory.create_campaign(
        db, 1, selection["id"], "Smart Regression", environment_id=3
    )
    assert campaign["campaign_type"] == "CUSTOM"
    assert campaign["scenario_count"] == len(selection["selected"])
    row = db.get(ExecutionCampaign, campaign["campaign_id"])
    assert row is not None and row.status == "DRAFT"
    rows = (
        db.query(CampaignScenario)
        .filter(CampaignScenario.campaign_id == campaign["campaign_id"])
        .all()
    )
    assert len(rows) == campaign["scenario_count"]
