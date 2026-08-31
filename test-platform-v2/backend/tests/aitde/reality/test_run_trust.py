"""V3.9-R1 TRUST-007 — run trust level computation."""
from __future__ import annotations

from app.modules.aitde.common.enums import AssertionTrustStatus
from app.modules.aitde.execution.outcome_classifier import compute_run_trust
from app.modules.aitde.execution.models import AssertionResult


def test_run_trust_trusted_when_all_test_oracle():
    a = AssertionResult(oracle_source_type="TEST_ORACLE", trust_status="TRUSTED")
    assert compute_run_trust([a]) == AssertionTrustStatus.TRUSTED.value


def test_run_trust_legacy_unverified_when_any_legacy():
    legacy = AssertionResult(oracle_source_type="LEGACY_COMMAND_ASSERT", trust_status="LEGACY_UNVERIFIED")
    trusted = AssertionResult(oracle_source_type="TEST_ORACLE", trust_status="TRUSTED")
    assert compute_run_trust([legacy]) == AssertionTrustStatus.LEGACY_UNVERIFIED.value
    assert compute_run_trust([legacy, trusted]) == AssertionTrustStatus.LEGACY_UNVERIFIED.value


def test_run_trust_invalid_when_invalid():
    a = AssertionResult(oracle_source_type="TEST_ORACLE", trust_status="INVALID")
    assert compute_run_trust([a]) == AssertionTrustStatus.INVALID.value


def test_run_trust_no_assertions_is_legacy_unverified():
    assert compute_run_trust([]) == AssertionTrustStatus.LEGACY_UNVERIFIED.value
