"""M4 / TA-026：Defect Draft + Link 单测。"""
from __future__ import annotations

import pytest

from app.models.defect import Defect
from app.services.defect_service import (
    _defect_to_dict,
    create_draft_from_failure,
)


def steps():
    return [
        {"action": "打开直播入口", "expected": "入口可见", "evidence_ref": "artifact:dom-1"},
        {"action": "点击直播卡片", "expected": "进入播放页", "evidence_ref": "artifact:trace-1"},
    ]


def draft(db_session, **overrides):
    payload = {
        "project_id": 1,
        "title": "直播入口点击无响应",
        "run_id": "run-1",
        "node_run_id": "node-1",
        "reproduction_steps": steps(),
        "evidence_refs": ["artifact:trace-1", "event:104"],
        "ac_refs": ["AC-001"],
        "creator_id": 7,
    }
    payload.update(overrides)
    return create_draft_from_failure(db_session, **payload)


def test_create_draft_with_structured_reproduction(db_session):
    row = draft(db_session)
    assert row.is_draft is True
    assert row.status == "open"
    assert row.defect_id.startswith("DEF-")
    assert row.aiqe_run_id == "run-1" and row.aiqe_node_run_id == "node-1"
    assert row.ac_refs_json == ["AC-001"]
    assert row.evidence_refs_json == ["artifact:trace-1", "event:104"]
    assert len(row.reproduction_steps_json) == 2

    detail = _defect_to_dict(row)
    assert detail["aiqe_run_id"] == "run-1"
    assert detail["ac_refs"] == ["AC-001"]
    assert detail["reproduction_steps"][0]["action"] == "打开直播入口"


def test_missing_action_rejected(db_session):
    with pytest.raises(ValueError):
        draft(db_session, reproduction_steps=[{"expected": "x"}])


def test_missing_expected_rejected(db_session):
    with pytest.raises(ValueError):
        draft(db_session, reproduction_steps=[{"action": "x"}])


def test_empty_steps_rejected(db_session):
    with pytest.raises(ValueError):
        draft(db_session, reproduction_steps=[])


def test_empty_evidence_rejected(db_session):
    with pytest.raises(ValueError):
        draft(db_session, evidence_refs=[])


def test_invalid_evidence_prefix_rejected(db_session):
    with pytest.raises(ValueError):
        draft(db_session, evidence_refs=["https://evil"])


def test_ac_required_and_valid(db_session):
    with pytest.raises(ValueError):
        draft(db_session, ac_refs=[])
    with pytest.raises(ValueError):
        draft(db_session, ac_refs=["REQ-1"])


def test_idempotent_same_run_and_title(db_session):
    first = draft(db_session)
    second = draft(db_session)
    assert first.id == second.id
    assert db_session.query(Defect).count() == 1
