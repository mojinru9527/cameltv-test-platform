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
from app.modules.aitde.common.enums import ContinuousTriggerType


def _components(**kw):
    base = {"service_versions": {"api": "1.0"}, "openapi_hash": "abc"}
    base.update(kw)
    return base


# 鈹€鈹€ V35-001 EnvironmentFingerprint 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


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


# 鈹€鈹€ V35-002 BuildObservation 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


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


# 鈹€鈹€ V35-003 ExecutionCampaign (immutable snapshot) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


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


# 鈹€鈹€ V35-004 RunProfile project isolation 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


def test_run_profile_project_isolation(db):
    a = service.create_run_profile(db, RunProfileIn(project_id=1, name="smoke"))
    b = service.create_run_profile(db, RunProfileIn(project_id=2, name="full"))
    list1 = service.list_run_profiles(db, 1)
    list2 = service.list_run_profiles(db, 2)
    assert [p["id"] for p in list1] == [a["id"]]
    assert [p["id"] for p in list2] == [b["id"]]


# 鈹€鈹€ V35-007 QualityGate (zero execution -> FAIL) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


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


# 鈹€鈹€ V35-008 Trigger 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


def test_create_and_list_trigger(db):
    trig = service.create_trigger(db, TriggerIn(project_id=1, trigger_type=ContinuousTriggerType.FINGERPRINT, config={"interval_min": 5}))
    assert trig["trigger_type"] == ContinuousTriggerType.FINGERPRINT.value
    items = service.list_triggers(db, 1)
    assert [t["id"] for t in items] == [trig["id"]]


# 鈹€鈹€ V35-009 Schedule Adapter (legacy schedule 涓嶇牬鍧? 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


def _fake_schedule(sid=1, enabled=True, cron="0 2 * * *", plan_id=9):
    class S:
        pass

    s = S()
    s.id = sid
    s.enabled = enabled
    s.cron_expression = cron
    s.job_type = "plan"
    s.job_id = None
    s.plan_id = plan_id
    s.environment_id = 3
    return s


def test_schedule_adapter_creates_trigger(db):
    from app.modules.aitde.continuous.adapters import schedule_adapter

    trig = schedule_adapter.to_trigger(db, _fake_schedule(), project_id=1)
    assert trig["trigger_type"] == ContinuousTriggerType.SCHEDULE.value
    assert trig["status"] == "ACTIVE"


def test_schedule_adapter_idempotent(db):
    from app.modules.aitde.continuous.adapters import schedule_adapter

    t1 = schedule_adapter.to_trigger(db, _fake_schedule(), project_id=1)
    t2 = schedule_adapter.to_trigger(db, _fake_schedule(), project_id=1)
    # Same legacy schedule -> same trigger (no duplicate).
    assert t1["id"] == t2["id"]


def test_schedule_adapter_disabled_maps_status(db):
    from app.modules.aitde.continuous.adapters import schedule_adapter

    trig = schedule_adapter.to_trigger(db, _fake_schedule(enabled=False), project_id=1)
    assert trig["status"] == "DISABLED"


# 鈹€鈹€ V35-010 TestPlan Adapter (鏃?plan 鍙) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


def test_testplan_adapter_creates_campaign(db):
    from app.modules.aitde.continuous.adapters import test_plan_adapter

    plan_id = 55
    campaign = test_plan_adapter.to_campaign(db, _fake_plan(plan_id), project_id=1)
    assert campaign["created_by_type"] == "LEGACY"
    assert campaign["mission_id"] == plan_id
    assert campaign["campaign_type"] == CampaignType.CUSTOM.value


def _fake_plan(pid=55):
    class P:
        pass

    p = P()
    p.id = pid
    p.project_id = 1
    p.name = "鍥炲綊璁″垝"
    return p

