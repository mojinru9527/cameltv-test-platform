"""M4 / TA-027：一键回归 + Run 对比单测。"""
from __future__ import annotations

import pytest

from app.models.defect import Defect, DefectRegression
from app.services.defect_service import compare_runs, create_regression


def make_defect(db_session) -> Defect:
    row = Defect(project_id=1, title="直播入口无响应", severity="P1", status="open")
    db_session.add(row)
    db_session.flush()
    return row


def test_create_regression_records_runs(db_session):
    defect = make_defect(db_session)
    row = create_regression(
        db_session,
        defect_id=defect.id,
        fixed_sha="abc1234def",
        previous_run_id="run-old",
        verification_run_id="run-new",
    )
    assert row.fixed_sha == "abc1234def"
    assert row.previous_run_id == "run-old"
    assert row.verification_run_id == "run-new"
    assert row.status == "passed"


def test_pending_regression_without_verification_run(db_session):
    defect = make_defect(db_session)
    row = create_regression(db_session, defect_id=defect.id, fixed_sha="abc1234")
    assert row.status == "pending"
    assert row.verification_run_id is None


def test_unknown_defect_rejected(db_session):
    with pytest.raises(ValueError):
        create_regression(db_session, defect_id=999, fixed_sha="abc1234")


def test_short_sha_rejected(db_session):
    defect = make_defect(db_session)
    with pytest.raises(ValueError):
        create_regression(db_session, defect_id=defect.id, fixed_sha="abc")


def test_compare_runs_fixed_regressed_failing(db_session):
    previous = [
        {"assertion_key": "AC1", "status": "FAIL"},
        {"assertion_key": "AC2", "status": "PASS"},
        {"assertion_key": "AC3", "status": "FAIL"},
    ]
    current = [
        {"assertion_key": "AC1", "status": "PASS"},
        {"assertion_key": "AC2", "status": "FAIL"},
        {"assertion_key": "AC3", "status": "FAIL"},
        {"assertion_key": "AC4", "status": "PASS"},
    ]
    diff = compare_runs(previous, current)
    assert diff["fixed"] == ["AC1"]
    assert diff["regressed"] == ["AC2"]
    assert diff["still_failing"] == ["AC3"]
    assert diff["new_assertions"] == ["AC4"]
    assert diff["total_previous"] == 3 and diff["total_current"] == 4


def test_compare_does_not_mutate_previous(db_session):
    previous = [{"assertion_key": "AC1", "status": "FAIL"}]
    snapshot = [dict(item) for item in previous]
    compare_runs(previous, [{"assertion_key": "AC1", "status": "PASS"}])
    assert previous == snapshot


def test_regression_rows_persisted_per_attempt(db_session):
    defect = make_defect(db_session)
    create_regression(db_session, defect_id=defect.id, fixed_sha="sha-0001", verification_run_id="run-1")
    create_regression(db_session, defect_id=defect.id, fixed_sha="sha-0002", verification_run_id="run-2")
    assert db_session.query(DefectRegression).filter_by(defect_id=defect.id).count() == 2
