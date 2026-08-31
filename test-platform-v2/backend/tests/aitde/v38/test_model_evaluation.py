"""AITDE V3.8 model evaluation + auto-retry policy tests.

V38-013 Golden model evaluation (regression threshold), V38-014 AutoRetryPolicy
(transient / approved-healing only; BusinessFail never infinite-retries).
"""

from __future__ import annotations

from app.modules.aitde.ai_closed_loop import service
from app.modules.aitde.browser.models import HealingProposal
from app.modules.aitde.common.enums import (
    AutoRetryDecision,
    HealingProposalStatus,
)
from app.modules.aitde.execution.models import ExecutionRun


def _run(db, outcome, run_id):
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


def test_model_evaluation_records_and_lists(db):
    service.PromptEvaluationService.evaluate(
        db,
        {
            "evaluation_suite": "failure-triage-golden",
            "model_ref": "deepseek-v4",
            "prompt_versions": ["v1", "v2"],
            "metrics": {"accuracy": 0.92, "n": 100},
        },
    )
    rows = service.PromptEvaluationService.list(db)
    assert len(rows) == 1
    assert rows[0]["evaluation_suite"] == "failure-triage-golden"
    assert rows[0]["metrics"]["accuracy"] == 0.92


def test_regression_check_below_threshold_blocks(db):
    service.PromptEvaluationService.evaluate(
        db,
        {
            "evaluation_suite": "golden",
            "model_ref": "old",
            "metrics": {"accuracy": 0.95},
        },
    )
    service.PromptEvaluationService.evaluate(
        db,
        {
            "evaluation_suite": "golden",
            "model_ref": "new",
            "metrics": {"accuracy": 0.85},
        },
    )
    check = service.PromptEvaluationService.check_regression(db, "golden")
    assert check["passed"] is False
    assert check["score"] == 0.85


def test_regression_check_insufficient_samples_is_blocked(db):
    # V3.9-R5 (AI-004): <2 runs must be BLOCKED, never passed.
    service.PromptEvaluationService.evaluate(
        db,
        {
            "evaluation_suite": "golden",
            "model_ref": "only-run",
            "metrics": {"accuracy": 0.99},
        },
    )
    check = service.PromptEvaluationService.check_regression(db, "golden")
    assert check["passed"] is False
    assert check["ok"] is False
    assert check["status"] == "BLOCKED"
    assert check["reason"] == "INSUFFICIENT_SAMPLES"


def test_auto_retry_never_retries_business_fail(db):
    _run(db, "BUSINESS_FAIL", 1)
    decision = service.AutoRetryPolicy.decide(db, 1)
    assert decision["decision"] == AutoRetryDecision.NO_RETRY.value
    assert "never auto-retried" in decision["reason"]


def test_auto_retry_transient_and_approved_healing(db):
    _run(db, "ENV_FAIL", 2)
    assert (
        service.AutoRetryPolicy.decide(db, 2)["decision"]
        == AutoRetryDecision.RETRY.value
    )
    # approved healing proposal enables retry even on a transient-ish outcome
    p = HealingProposal(
        scenario_adapter_id=10,
        command_plan_version_id=1,
        proposal_type="LOCATOR",
        before_json="{}",
        after_json="{}",
        reason="x",
        status=HealingProposalStatus.APPROVED.value,
        created_by_type="AI",
    )
    db.add(p)
    db.flush()
    _run(db, "AUTOMATION_FAIL", 3)
    decision = service.AutoRetryPolicy.decide(db, 3, p.id)
    assert decision["decision"] == AutoRetryDecision.RETRY.value
