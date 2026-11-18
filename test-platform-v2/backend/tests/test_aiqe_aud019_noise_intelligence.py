"""AUD-019：Noise Intelligence 12 类干扰 / Observation / Triage 生命周期 / 规则治理。

对应 v1.5 §03 AUD-019 与 §04：
- 12 类干扰都有确定性 Detector 与建议实验 E1–E6；
- Detector 只写 Observation，不修改 Run Outcome；
- TriageCase 生命周期不可跳级；
- Noise Rule 必须人工批准、90 天到期、续期新建版本，且 P0 永不可被抑制。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.aiqe.models.interference import InterferenceObservation, TriageCase
from app.aiqe.models.noise_rule import NoiseRule
from app.aiqe.models.run import TestRun
from app.aiqe.services import interference_service
from app.aiqe.services.noise_intelligence import (
    CATEGORIES,
    CATEGORY_OF_DETECTOR,
    EXPERIMENT_OF_CATEGORY,
    TRIAGE_LIFECYCLE,
    NoiseIntelligenceError,
    create_triage_case,
    detect_categories,
    list_observations,
    persist_observations,
    suppression_allowed,
    transition_triage_case,
)
from app.aiqe.services.noise_rule_service import (
    NoiseRuleError,
    approve_rule,
    create_rule,
    get_rule,
    is_effective,
    record_match,
    renew_rule,
)


def _run(db, *, key="RUN-NOISE-1") -> TestRun:
    run = TestRun(project_id=1, run_key=key, status="COMPLETED", outcome="FAIL")
    db.add(run)
    db.commit()
    return run


# ── 1. 12 类检测与建议实验 ───────────────────────────────
def test_all_legacy_detectors_map_to_spec_categories():
    assert len(CATEGORIES) == 12
    assert set(CATEGORY_OF_DETECTOR) == set(interference_service.KINDS)
    for kind in interference_service.KINDS:
        assert CATEGORY_OF_DETECTOR[kind] in CATEGORIES


@pytest.mark.parametrize(
    ("payload", "category", "experiment"),
    [
        ({"cpu": {"throttled_seconds": 3}}, "ENVIRONMENT", "E5"),
        ({"fixture": {"conflict": True, "namespace": "ns-1"}}, "TEST_DATA", "E2"),
        ({"lock": {"wait_ms": 5000}}, "CONCURRENCY", "E2"),
        ({"dependency": {"upstream_5xx": 2}}, "THIRD_PARTY", "E3"),
        ({"network": {"p95_latency_ms": 900}}, "NETWORK", "E6"),
        ({"clock": {"skew_ms": 4200}}, "TIME", "E1"),
        ({"feature_flag": {"changed": True, "name": "ad_overlay"}}, "CROSS_FEATURE", "E4"),
        ({"ui": {"overlap_ratio": 0.93, "target": "live-entry"}}, "UI_OVERLAY", "E4"),
        ({"runner": {"crash": True, "id": "runner-1"}}, "AUTOMATION", "E5"),
        ({"requirement": {"missing_ac": True, "id": "REQ-1"}}, "REQUIREMENT_GAP", "E1"),
        ({"runs": {"results": ["PASS", "FAIL"]}}, "FLAKY", "E1"),
    ],
)
def test_each_category_detected_with_experiment(payload, category, experiment):
    detections = detect_categories(payload)
    assert any(item.category == category for item in detections), detections
    hit = next(item for item in detections if item.category == category)
    assert hit.recommended_experiment == experiment


def test_unknown_fallback_keeps_unknown_category():
    detections = detect_categories({"nothing": True})
    assert [item.category for item in detections] == ["UNKNOWN"]
    assert detections[0].recommended_experiment == EXPERIMENT_OF_CATEGORY["UNKNOWN"]


def test_detectors_are_deterministic():
    payload = {"ui": {"overlap_ratio": 0.95}, "runner": {"crash": True}}
    first = [item.payload() for item in detect_categories(payload)]
    second = [item.payload() for item in detect_categories(payload)]
    assert first == second


# ── 2. Observation 持久化不修改 Run ──────────────────────
def test_observations_persisted_without_touching_run(db_session):
    run = _run(db_session)
    observed = datetime.now(UTC)
    detections = detect_categories({"ui": {"overlap_ratio": 0.93, "evidence_refs": ["artifact:1"]}})
    rows = persist_observations(
        db_session,
        project_id=1,
        run_id=run.id,
        detections=detections,
        observed_at=observed,
    )
    db_session.commit()

    assert rows and rows[0].category == "UI_OVERLAY"
    assert rows[0].detector_key == "ui_overlay_hit_target"
    assert rows[0].evidence_refs_json == ["artifact:1"]
    assert rows[0].window_start is not None and rows[0].window_end is not None
    assert rows[0].recommended_experiment == "E4"

    db_session.expire_all()
    assert db_session.get(TestRun, run.id).outcome == "FAIL"  # 原始结论不被改写
    listed = list_observations(db_session, project_id=1, run_id=run.id)
    assert len(listed) == len(rows)
    assert list_observations(db_session, project_id=2, run_id=run.id) == []


# ── 3. TriageCase 生命周期 ───────────────────────────────
def test_triage_lifecycle_rejects_skipped_states(db_session):
    run = _run(db_session, key="RUN-NOISE-2")
    case = create_triage_case(db_session, project_id=1, run_id=run.id, node_run_id=None)
    assert case.status == "DETECTED"
    with pytest.raises(NoiseIntelligenceError):
        transition_triage_case(
            db_session, triage_id=case.id, project_id=1, target="EXPERIMENT_RUNNING"
        )
    for target in (
        "EVIDENCE_COLLECTED",
        "HYPOTHESES_READY",
        "EXPERIMENT_PROPOSED",
        "EXPERIMENT_RUNNING",
        "ATTRIBUTED",
    ):
        transition_triage_case(db_session, triage_id=case.id, project_id=1, target=target)
    db_session.commit()
    db_session.expire_all()
    row = db_session.get(TriageCase, case.id)
    assert row.status == "ATTRIBUTED"
    assert row.status in TRIAGE_LIFECYCLE
    with pytest.raises(NoiseIntelligenceError):
        transition_triage_case(db_session, triage_id=case.id, project_id=1, target="DETECTED")


def test_triage_case_project_scope(db_session):
    run = _run(db_session, key="RUN-NOISE-3")
    case = create_triage_case(db_session, project_id=1, run_id=run.id)
    with pytest.raises(NoiseIntelligenceError):
        transition_triage_case(db_session, triage_id=case.id, project_id=2, target="UNKNOWN")


# ── 4. Noise Rule 治理 ──────────────────────────────────
def test_rule_requires_approval_before_effective(db_session):
    rule = create_rule(
        db_session,
        project_id=1,
        pattern="广告抖动",
        action="suppress",
        reason="已知广告抖动",
        detector_key="ui_overlay_hit_target",
    )
    assert rule.status == "pending_approval"
    assert is_effective(rule) is False
    with pytest.raises(NoiseRuleError):
        create_rule(db_session, project_id=1, pattern="无原因", action="suppress")

    approved = approve_rule(db_session, rule.id, project_id=1, approved_by=9)
    assert approved.status == "active"
    assert approved.approved_by == 9
    assert is_effective(approved) is True

    with pytest.raises(NoiseRuleError):
        get_rule(db_session, rule.id, project_id=2)


def test_p0_cannot_be_suppressed():
    assert suppression_allowed(category="UI_OVERLAY", priority="P0", action="suppress") is False
    assert suppression_allowed(category="UI_OVERLAY", priority="P0", action="quarantine") is False
    assert suppression_allowed(category="UI_OVERLAY", priority="P1", action="suppress") is True


def test_rule_metadata_and_counters(db_session):
    rule = create_rule(
        db_session,
        project_id=1,
        pattern="网络抖动",
        action="hint",
        environment_id=3,
        profile_id="profile-1",
        detector_key="network_latency",
        error_class="NETWORK",
        selector={"node_key": "verify_public_api"},
        app_version="14.1.0",
        evidence_refs=["artifact:9"],
        reason="历史网络问题",
        require_approval=False,
    )
    assert rule.version == 1
    assert rule.matched_count == 0
    record_match(db_session, rule.id, suppressed=True, false_suppress=True)
    assert rule.matched_count == 1
    assert rule.false_suppress_count == 1


def test_renew_creates_new_version_and_requires_approval(db_session):
    rule = create_rule(
        db_session,
        project_id=1,
        pattern="环境抖动",
        action="hint",
        reason="环境不稳定",
        require_approval=False,
    )
    renewed = renew_rule(db_session, rule.id, project_id=1)
    db_session.commit()
    assert renewed.version == 2
    assert renewed.supersedes_id == rule.id
    assert renewed.status == "pending_approval"
    db_session.expire_all()
    assert db_session.get(NoiseRule, rule.id).status == "superseded"


def test_expiry_enforced(db_session):
    rule = create_rule(
        db_session,
        project_id=1,
        pattern="短效",
        action="hint",
        reason="x",
        require_approval=False,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    assert is_effective(rule) is True
    rule.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    assert is_effective(rule) is False
    assert list(db_session.scalars(select(InterferenceObservation))) == []
