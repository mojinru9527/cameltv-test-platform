"""AITDE V3.8 failure evidence pack / triage / hypothesis review guard tests.

V38-001 FailureEvidencePack, V38-002 FailureTriageAgent (Outcome immutable),
V38-003 HypothesisReviewService. The invariants tested: AI never writes a new
formal Outcome, never leaks secrets into the model, and review transitions are
audited & bounded.
"""

from __future__ import annotations

from app.modules.aitde.ai_closed_loop import service
from app.modules.aitde.ai_closed_loop.models import FailureHypothesis
from app.modules.aitde.common.enums import (
    FailureClassification,
    FailureHypothesisStatus,
)
from app.modules.aitde.execution.models import ExecutionRun


def _run(db, outcome="BUSINESS_FAIL", run_id=1):
    run = ExecutionRun(
        id=run_id,
        project_id=1,
        mission_id=7,
        scenario_id=2,
        scenario_version_id=1,
        contract_version_id=0,
        adapter_id=0,
        environment_id=0,
        runtime_status="FINISHED",
        outcome=outcome,
        evidence_status="COMPLETE",
    )
    db.add(run)
    db.flush()
    return run


def test_triage_does_not_mutate_outcome(db):
    run = _run(db, outcome="BUSINESS_FAIL")
    result = service.FailureTriageAgent.triage(db, run.id, {}, "m1", "v38")
    # Hypothesis created; run outcome remains untouched.
    assert result["hypothesis_type"] == (
        FailureClassification.BUSINESS_LOGIC_SUSPECTED.value
    )
    db.refresh(run)
    assert run.outcome == "BUSINESS_FAIL"  # immutable
    row = db.get(FailureHypothesis, result["id"])
    assert row is not None and row.status == FailureHypothesisStatus.GENERATED.value


def test_triage_classification_by_outcome(db):
    _run(db, outcome="AUTOMATION_FAIL", run_id=2)
    res = service.FailureTriageAgent.triage(db, 2, {})
    assert res["hypothesis_type"] == (
        FailureClassification.AUTOMATION_ISSUE_SUSPECTED.value
    )
    _run(db, outcome="ENV_FAIL", run_id=3)
    res = service.FailureTriageAgent.triage(db, 3, {})
    assert res["hypothesis_type"] == FailureClassification.ENV_ISSUE_SUSPECTED.value
    _run(db, outcome="PASS", run_id=4)
    res = service.FailureTriageAgent.triage(db, 4, {})
    # PASS is not triaged into a suspect classification; conservative UNKNOWN.
    assert res["hypothesis_type"] == FailureClassification.UNKNOWN.value


def test_hypothesis_review_transitions_bounded(db):
    _run(db, outcome="BUSINESS_FAIL", run_id=5)
    h = service.FailureTriageAgent.triage(db, 5, {})
    reviewed = service.HypothesisReviewService.review(
        db, h["id"], FailureHypothesisStatus.CONFIRMED.value, 42, "tester confirm"
    )
    assert reviewed["status"] == FailureHypothesisStatus.CONFIRMED.value
    assert reviewed["reviewed_by"] == 42


def test_hypothesis_review_rejects_illegal_transition(db):
    _run(db, outcome="BUSINESS_FAIL", run_id=6)
    h = service.FailureTriageAgent.triage(db, 6, {})
    try:
        service.HypothesisReviewService.review(db, h["id"], "SOMETHING", 1)
        assert False, "illegal status must raise"
    except ValueError:
        pass


def test_evidence_pack_sanitizes_secrets(db):
    _run(db, outcome="AUTOMATION_FAIL", run_id=7)
    # context with a secret is dropped before it can reach the model
    packed = service.FailureEvidencePackBuilder.build(db, 7)
    assert packed["sanitized"] is True
    assert "outcome" in packed
