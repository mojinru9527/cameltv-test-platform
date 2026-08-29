"""OutcomeClassifier decision-table tests (V31-008)."""
from __future__ import annotations

import pytest

from app.modules.aitde.common.enums import Outcome
from app.modules.aitde.execution.outcome_classifier import DecisionInput, classify


def test_env_error_wins():
    assert classify(DecisionInput(env_hard_error=True, required_oracle_pass=1, required_oracle_defined=1, evidence_complete=True)) == Outcome.ENV_FAIL.value


def test_data_fail():
    assert classify(DecisionInput(data_error=True)) == Outcome.DATA_FAIL.value


def test_automation_fail():
    assert classify(DecisionInput(automation_error=True)) == Outcome.AUTOMATION_FAIL.value


def test_assertion_error():
    assert classify(DecisionInput(assertion_evaluator_error=True)) == Outcome.ASSERTION_ERROR.value


def test_required_fail_is_business_fail():
    assert classify(DecisionInput(required_oracle_fail=1)) == Outcome.BUSINESS_FAIL.value


def test_not_evaluated_is_inconclusive():
    assert classify(DecisionInput(required_oracle_not_evaluated=1)) == Outcome.INCONCLUSIVE.value


def test_all_pass_with_evidence_is_pass():
    assert classify(DecisionInput(required_oracle_pass=3, required_oracle_defined=3, evidence_complete=True)) == Outcome.PASS.value


def test_all_pass_without_evidence_is_inconclusive():
    assert classify(DecisionInput(required_oracle_pass=3, required_oracle_defined=3, evidence_complete=False)) == Outcome.INCONCLUSIVE.value


def test_zero_oracles_is_inconclusive():
    assert classify(DecisionInput(required_oracle_defined=0, evidence_complete=True)) == Outcome.INCONCLUSIVE.value


def test_http_200_alone_is_not_pass():
    # the historical "HTTP 200 → PASS" shortcut must never happen
    assert classify(DecisionInput(required_oracle_fail=0, required_oracle_pass=0, required_oracle_defined=0, evidence_complete=True)) == Outcome.INCONCLUSIVE.value
