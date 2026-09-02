"""Batch 207 — closed-loop wiring reality tests.

A failing run is auto-tried on finish (rule-based, idempotent); confirming a
hypothesis feeds the suggestion inbox (producer).
"""
from __future__ import annotations

import pytest

from app.modules.aitde.ai_closed_loop import service as loop_service
from app.modules.aitde.ai_closed_loop.models import FailureHypothesis
from app.modules.aitde.common.enums import Outcome, RunStatus
from app.modules.aitde.execution import service as exec_service
from app.modules.aitde.execution.models import ExecutionRun
from app.modules.aitde.mission.models import Mission


def _failing_run(db, outcome: str):
    m = Mission(project_id=1, title="V207-loop", created_by=9)
    db.add(m)
    db.flush()
    run = ExecutionRun(
        project_id=1,
        mission_id=m.id,
        scenario_id=0,
        scenario_version_id=0,
        contract_version_id=0,
        runtime_status=RunStatus.RUNNING.value,
        created_by=9,
    )
    db.add(run)
    db.commit()
    return m, run


def test_auto_triage_on_failing_finish_is_idempotent(db):
    _m, run = _failing_run(db, None)
    finished = exec_service.finish_run(
        db, run.id, 1, Outcome.AUTOMATION_FAIL.value
    )
    assert finished.outcome == Outcome.AUTOMATION_FAIL.value
    hypotheses = db.query(FailureHypothesis).filter_by(run_id=run.id).all()
    assert len(hypotheses) == 1
    assert hypotheses[0].status == "GENERATED"
    # idempotent: second auto-triage adds nothing
    again = loop_service.FailureTriageAgent.auto_triage_if_needed(db, run.id)
    assert again is None
    assert db.query(FailureHypothesis).filter_by(run_id=run.id).count() == 1


def test_auto_triage_skips_pass_runs(db):
    _m, run = _failing_run(db, None)
    exec_service.finish_run(db, run.id, 1, Outcome.PASS.value)
    assert db.query(FailureHypothesis).filter_by(run_id=run.id).count() == 0


def test_confirm_hypothesis_creates_triage_suggestion(db):
    _m, run = _failing_run(db, None)
    exec_service.finish_run(db, run.id, 1, Outcome.BUSINESS_FAIL.value)
    hyp = db.query(FailureHypothesis).filter_by(run_id=run.id).one()
    loop_service.HypothesisReviewService.review(
        db, hyp.id, "CONFIRMED", reviewed_by=9, reason="confirmed by tester"
    )
    items = loop_service.SuggestionInboxService.list(db, project_id=1)
    assert any(
        s["suggestion_type"] == "TRIAGE" and s["target_id"] == run.id
        for s in items
    )
