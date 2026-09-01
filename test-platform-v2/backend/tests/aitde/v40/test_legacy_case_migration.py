"""AITDE V4.0 (V40-005) high-value legacy case migration workflow tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.test_case import TestCase as CaseModel
from app.modules.aitde.legacy_cutover import service as cutover_service
from app.modules.aitde.legacy_cutover.models import LegacyCaseMigration, LegacyObjectMapping
from app.modules.aitde.legacy_cutover.service import LegacyCaseMigrationService as Svc
from app.modules.aitde.scenario.models import TestScenario as ScenarioModel
from app.modules.aitde.scenario.models import TestScenarioVersion as ScenarioVersionModel


def _add_case(db, project_id=1, priority="P0", key="TC-V4-001"):
    case = CaseModel(project_id=project_id, title="高价值用例", case_type="api", priority=priority, case_id=key)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def test_enqueue_selects_high_value_and_skips_migrated(db):
    p0 = _add_case(db, priority="P0", key="TC-P0-1")
    _add_case(db, priority="P2", key="TC-P2-1")  # low value: must NOT be enqueued
    rows = Svc.enqueue_high_value(db, 1)
    # Only P0/P1 enqueued (p2 excluded); idempotency: re-enqueue does not duplicate.
    assert [r["source_case_id"] for r in rows] == [p0.id]
    rows2 = Svc.enqueue_high_value(db, 1)
    assert rows2 == []


def test_full_review_and_promote_flow(db):
    case = _add_case(db, priority="P1", key="TC-P1-2")
    migrated = Svc.enqueue_high_value(db, 1)
    mig_id = migrated[0]["id"]

    # Cannot review before a draft is supplied.
    with pytest.raises(ValueError):
        Svc.submit_review(db, mig_id, "ACCEPTED", reviewer_id=7)

    with pytest.raises(ValueError):
        Svc.submit_draft(db, mig_id, 0, draft={"given": {}})  # mission_id must be > 0

    draft = {
        "title": "登录成功",
        "goal": "校验登录主流程",
        "given": {"user": "prepared"},
        "when": {"action": "login"},
        "expected": {"status": 200},
    }
    done = Svc.submit_draft(db, mig_id, mission_id=9, contract_version_id=3, draft=draft)
    assert done["status"] == "AWAITING_REVIEW"

    acc = Svc.submit_review(db, mig_id, "ACCEPTED", reviewer_id=7)
    assert acc["status"] == "ACCEPTED"

    promoted = Svc.promote(db, mig_id)
    assert promoted["status"] == "MIGRATED"
    assert promoted["scenario_id"] is not None

    scenario = db.get(ScenarioModel, promoted["scenario_id"])
    assert scenario is not None
    assert scenario.mission_id == 9
    assert (
        db.scalar(
            select(ScenarioVersionModel).where(
                ScenarioVersionModel.scenario_id == scenario.id
            )
        )
        is not None
    )
    # A real TEST_CASE -> TEST_SCENARIO mapping was recorded + verified.
    mapping = db.scalar(
        select(LegacyObjectMapping).where(
            LegacyObjectMapping.legacy_type == "TEST_CASE",
            LegacyObjectMapping.legacy_id == case.id,
        )
    )
    assert mapping is not None
    assert mapping.canonical_type == "TEST_SCENARIO"
    assert mapping.migration_status == "VERIFIED"


def test_reject_blocks_promote(db):
    _add_case(db, priority="P0", key="TC-P0-3")
    mig_id = Svc.enqueue_high_value(db, 1)[0]["id"]
    Svc.submit_draft(db, mig_id, mission_id=9, draft={"given": {}, "when": {}, "expected": {}})
    rejected = Svc.submit_review(db, mig_id, "REJECTED", reviewer_id=7)
    assert rejected["status"] == "REJECTED"
    with pytest.raises(ValueError):
        Svc.promote(db, mig_id)


def test_promote_requires_accepted_and_mission(db):
    _add_case(db, priority="P0", key="TC-P0-4")
    mig_id = Svc.enqueue_high_value(db, 1)[0]["id"]
    # Not accepted yet -> cannot promote.
    with pytest.raises(ValueError):
        Svc.promote(db, mig_id)


def test_generate_ai_draft_extracts_and_awaits_review(db, monkeypatch):
    _add_case(db, priority="P0", key="TC-AI-1")
    mig_id = Svc.enqueue_high_value(db, 1, mission_id=9)[0]["id"]
    draft = {
        "given": {"user": "prepared"},
        "when": {"action": "login"},
        "expected": {"status": 200},
        "title": "登录成功",
        "goal": "校验登录主流程",
    }
    monkeypatch.setattr(
        cutover_service, "extract_ai_draft", lambda project_id, case: {"ok": True, "draft": draft}
    )
    res = Svc.generate_ai_draft(db, mig_id)
    assert res["ok"] is True
    assert res["migration"]["status"] == "AWAITING_REVIEW"


def test_generate_ai_draft_ai_not_configured_stays_pending(db, monkeypatch):
    _add_case(db, priority="P1", key="TC-AI-2")
    mig_id = Svc.enqueue_high_value(db, 1, mission_id=9)[0]["id"]
    monkeypatch.setattr(
        cutover_service, "extract_ai_draft",
        lambda project_id, case: {"ok": False, "reason": "ai_not_configured"},
    )
    res = Svc.generate_ai_draft(db, mig_id)
    assert res["ok"] is False
    assert res["reason"] == "ai_not_configured"
    # Honest: stays DRAFT_PENDING, no fabricated draft.
    row = db.get(LegacyCaseMigration, mig_id)
    assert row.status == "DRAFT_PENDING"
    assert row.draft_json == "{}"
