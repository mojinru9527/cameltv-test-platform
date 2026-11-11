"""M5 / TA-030：Learning Curator 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.models.learning import BugPattern, LearningCandidate
from app.aiqe.services.learning_service import (
    LearningError,
    activate_candidate,
    approve_candidate,
    create_candidate,
    evaluate_candidate,
    list_candidates,
)


def candidate(db_session, **overrides):
    payload = {
        "project_id": 1,
        "rule": {"pattern": "广告遮挡入口", "description": "广告浮层导致点击失败"},
    }
    payload.update(overrides)
    return create_candidate(db_session, **payload)


def benchmark(rate=0.05, samples=50):
    return {"false_positive_rate": rate, "sample_size": samples, "precision": 1 - rate}


def test_create_and_validate(db_session):
    row = candidate(db_session)
    assert row.status == "draft"
    with pytest.raises(LearningError):
        create_candidate(db_session, project_id=1, rule={})


def test_benchmark_sets_status(db_session):
    row = candidate(db_session)
    evaluated = evaluate_candidate(db_session, row.id, benchmark())
    assert evaluated.status == "benchmarked"
    assert evaluated.benchmark_json["sample_size"] == 50


def test_invalid_benchmark_rejected(db_session):
    row = candidate(db_session)
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, row.id, {"sample_size": 10})
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, row.id, {"false_positive_rate": 0.1, "sample_size": 0})


def test_approve_requires_benchmark(db_session):
    row = candidate(db_session)
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id)


def test_high_false_positive_rejected(db_session):
    row = candidate(db_session)
    evaluate_candidate(db_session, row.id, benchmark(rate=0.35))
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id)


def test_duplicate_requires_acknowledgement(db_session):
    row = candidate(db_session, duplicate_of="existing-id")
    evaluate_candidate(db_session, row.id, benchmark())
    with pytest.raises(LearningError):
        approve_candidate(db_session, row.id)
    approved = approve_candidate(db_session, row.id, acknowledge_duplicate=True)
    assert approved.status == "approved"


def test_activate_creates_active_pattern(db_session):
    row = candidate(db_session)
    evaluate_candidate(db_session, row.id, benchmark())
    approve_candidate(db_session, row.id)
    pattern = activate_candidate(db_session, row.id)
    assert pattern is not None and pattern.status == "active"
    assert pattern.pattern_key == "广告遮挡入口"
    assert db_session.get(LearningCandidate, row.id).status == "active"


def test_duplicate_activation_merges_without_new_pattern(db_session):
    first = candidate(db_session)
    evaluate_candidate(db_session, first.id, benchmark())
    approve_candidate(db_session, first.id)
    activate_candidate(db_session, first.id)

    second = candidate(db_session, duplicate_of=first.id)
    evaluate_candidate(db_session, second.id, benchmark())
    approve_candidate(db_session, second.id, acknowledge_duplicate=True)
    assert activate_candidate(db_session, second.id) is None
    assert db_session.query(BugPattern).count() == 1


def test_same_pattern_key_merges(db_session):
    first = candidate(db_session)
    evaluate_candidate(db_session, first.id, benchmark())
    approve_candidate(db_session, first.id)
    activate_candidate(db_session, first.id)

    second = candidate(db_session)
    evaluate_candidate(db_session, second.id, benchmark())
    approve_candidate(db_session, second.id)
    pattern = activate_candidate(db_session, second.id)
    assert pattern is not None
    assert db_session.query(BugPattern).count() == 1
    assert db_session.get(LearningCandidate, second.id).duplicate_of == pattern.id


def test_list_candidates(db_session):
    candidate(db_session)
    candidate(db_session)
    assert len(list_candidates(db_session, 1)) == 2
