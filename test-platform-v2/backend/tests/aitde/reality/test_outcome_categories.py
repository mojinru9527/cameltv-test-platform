"""CERT-002 — outcome classifier maps each failure category correctly.

Drives the REAL ``outcome_classifier.classify`` decision table with each category's
signal and asserts it returns the exact frozen Outcome. This is the deterministic
guarantee that BUSINESS_FAIL / DATA_FAIL / ENV_FAIL / AUTOMATION_FAIL /
INCONCLUSIVE / PASS are never conflated (V31-008 forbids fake-pass shortcuts).
"""
from __future__ import annotations

from app.modules.aitde.common.enums import Outcome
from app.modules.aitde.execution.outcome_classifier import DecisionInput, classify


def _dec(**kw) -> str:
    return classify(DecisionInput(**kw))


def test_business_fail_when_required_oracle_fails():
    assert _dec(required_oracle_fail=1, required_oracle_defined=1) == Outcome.BUSINESS_FAIL.value


def test_data_fail_wins_over_business():
    # A data error is authoritative even if a business oracle would fail.
    assert _dec(data_error=True, required_oracle_fail=1, required_oracle_defined=1) == Outcome.DATA_FAIL.value


def test_env_fail_wins_over_all():
    assert _dec(env_hard_error=True, data_error=True, automation_error=True, required_oracle_fail=1) == Outcome.ENV_FAIL.value


def test_automation_fail_when_runtime_error():
    assert _dec(automation_error=True, required_oracle_fail=1) == Outcome.AUTOMATION_FAIL.value


def test_inconclusive_when_oracle_not_evaluated():
    assert _dec(required_oracle_not_evaluated=1, required_oracle_defined=1) == Outcome.INCONCLUSIVE.value


def test_assertion_evaluator_error_is_tooling():
    assert _dec(assertion_evaluator_error=True) == Outcome.ASSERTION_ERROR.value


def test_pass_only_when_all_required_pass_and_evidence_complete():
    assert _dec(required_oracle_pass=1, required_oracle_defined=1, evidence_complete=True) == Outcome.PASS.value


def test_not_a_pass_when_evidence_incomplete():
    # A required oracle passes but evidence is incomplete -> INCONCLUSIVE (never PASS).
    assert _dec(
        required_oracle_pass=1, required_oracle_defined=1, evidence_complete=False, evidence_failed=True
    ) == Outcome.INCONCLUSIVE.value


def test_zero_defined_is_inconclusive_never_pass():
    assert _dec(required_oracle_defined=0, evidence_complete=True) == Outcome.INCONCLUSIVE.value
