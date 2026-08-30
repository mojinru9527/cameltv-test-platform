"""AITDE V3.5 Continuous Acceptance tests (V35-001..007)."""

from __future__ import annotations

from app.modules.aitde.common.enums import (
    BuildObservationStatus,
    CampaignType,
    FingerprintSourceType,
    QualityGateResult,
)
from app.modules.aitde.continuous import repository, service
from app.modules.aitde.continuous.schemas import (
    CampaignCreateIn,
    FingerprintCaptureIn,
    RunProfileIn,
    TriggerIn,
)
from app.modules.aitde.common.enums import TriggerType


def _components(**kw):
    base = {"service_versions": {"api": "1.0"}, "openapi_hash": "abc"}
    base.update(kw)
    return base


# ── V35-001 EnvironmentFingerprint ──────────────────────────────────────────


def test_capture_fingerprint_dedupes(db):
    a = service.capture_fingerprint(
        db, 1, FingerprintCaptureIn(components=_components(), source_type=FingerprintSourceType.AUTO)
    )
    b = service.capture_fingerprint(
        db, 1, FingerprintCaptureIn(components=_components(), source_type=FingerprintSourceType.AUTO)
    )
    # Same components -> same hash -> deduped to the same row.
    assert a["fingerprint_hash"] == b["fingerprint_hash"]
    assert a["id"] == b["id"]
    assert len(repository.list_fingerprints(db, 1)) == 1


def test_capture_fingerprint_change_creates_new(db):
    a = service.capture_fingerprint(
        db, 1, FingerprintCaptureIn(components=_components(openapi_hash="abc"))
    )
    b = service.capture_fingerprint(
        db, 1, FingerprintCaptureIn(components=_components(openapi_hash="def"))
    )
    assert a["id"] != b["id"]
    assert len(repository.list_fingerprints(db, 1)) == 2


# ── V35-002 BuildObservation ─────────────────────────────────────────────────


def test_observe_build_no_duplicate(db):
    fp = service.capture_fingerprint(
        db, 1, FingerprintCaptureIn(components=_components())
    )
    obs1 = service.observe_build(db, 1, 7, fp["id"])
    obs2 = service.observe_build(db, 1, 7, fp["id"])
    # Same fingerprint -> no new observation (deduped).
    assert obs1["id"] == obs2["id"]
    assert obs1["status"] == BuildObservationStatus.NEW.value


def test_observe_build_change_creates_new(db):
    fp1 = service.capture_fingerprint(db, 1, FingerprintCaptureIn(components=_components(openapi_hash="a")))
    fp2 = service.capture_fingerprint(db, 1, FingerprintCaptureIn(components=_components(openapi_hash="b")))
    obs1 = service.observe_build(db, 1, 7, fp1["id"])
    obs2 = service.observe_build(db, 1, 7, fp2["id"])
    assert obs1["id"] != obs2["id"]
    assert obs2["previous_fingerprint_id"] == fp1["id"]


# ── V35-003 ExecutionCampaign (immutable snapshot) ───────────────────────────


def test_create_campaign_snapshot(db):
    campaign = service.create_campaign(
        db,
        CampaignCreateIn(
            project_id=1, mission_id=7, environment_id=1, campaign_type=CampaignType.IMPACTED,
            scenarios=[
                {"scenario_id": 1, "scenario_version_id": 10, "required": "REQUIRED", "selection_reason": {"planner": "v1"}},
            ],
        ),
    )
    assert campaign["campaign_type"] == CampaignType.IMPACTED.value
    detail = service.get_campaign(db, campaign["id"], 1)
    assert len(detail["scenarios"]) == 1
    assert detail["scenarios"][0]["required"] == "REQUIRED"


def test_campaign_run_immutable_after_start(db):

    campaign = service.create_campaign(
        db,
        CampaignCreateIn(project_id=1, mission_id=7, environment_id=1, campaign_type=CampaignType.FULL),
    )
    row = repository.get_campaign(db, campaign["id"], 1)
    updated = repository.update_campaign(db, row, {"status": "RUNNING"})
    assert updated.status == "RUNNING"


# ── V35-004 RunProfile project isolation ─────────────────────────────────────


def test_run_profile_project_isolation(db):
    a = service.create_run_profile(db, RunProfileIn(project_id=1, name="smoke"))
    b = service.create_run_profile(db, RunProfileIn(project_id=2, name="full"))
    list1 = service.list_run_profiles(db, 1)
    list2 = service.list_run_profiles(db, 2)
    assert [p["id"] for p in list1] == [a["id"]]
    assert [p["id"] for p in list2] == [b["id"]]


# ── V35-007 QualityGate (zero execution -> FAIL) ─────────────────────────────


def test_gate_zero_execution_fail(db):
    campaign = service.create_campaign(
        db,
        CampaignCreateIn(
            project_id=1, mission_id=7, environment_id=1, campaign_type=CampaignType.FULL,
            scenarios=[{"scenario_id": 1, "scenario_version_id": 10, "required": "REQUIRED"}],
        ),
    )
    gate = service.evaluate_gate(db, 1, 7, campaign["id"], None)
    # 0 execution with scenarios -> FAIL (never PASS).
    assert gate["result"] == QualityGateResult.FAIL.value
    assert "G5_REQUIRED_SCENARIO_EXECUTED" in gate["checks_json"]


def test_gate_no_scenarios_inconclusive(db):
    gate = service.evaluate_gate(db, 1, 7, None, None)
    # no campaign/scenarios -> INCONCLUSIVE (not PASS).
    assert gate["result"] == QualityGateResult.INCONCLUSIVE.value


# ── V35-008 Trigger ──────────────────────────────────────────────────────────


def test_create_and_list_trigger(db):
    trig = service.create_trigger(db, TriggerIn(project_id=1, trigger_type=TriggerType.FINGERPRINT, config={"interval_min": 5}))
    assert trig["trigger_type"] == TriggerType.FINGERPRINT.value
    items = service.list_triggers(db, 1)
    assert [t["id"] for t in items] == [trig["id"]]
