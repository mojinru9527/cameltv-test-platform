"""OutcomeClassifier (V31-008).

The deterministic decision table that turns a Run's assertion + evidence state
into a frozen Outcome. It explicitly forbids the historical fake-success
shortcuts (HTTP 200 -> PASS, toast -> PASS, script exception -> BUSINESS_FAIL).

This classifier has NO AI dependency and never invokes a model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.aitde.common.enums import AssertionTrustStatus, Outcome


@dataclass
class DecisionInput:
    """Aggregated, pre-computed signals for one Run."""

    env_hard_error: bool = False
    data_error: bool = False
    automation_error: bool = False
    assertion_evaluator_error: bool = False

    # Required oracles evaluated to FAIL
    required_oracle_fail: int = 0
    # Required oracles that could not be evaluated
    required_oracle_not_evaluated: int = 0
    # Required oracles that passed
    required_oracle_pass: int = 0
    # Number of required oracles defined (for the PASS gate)
    required_oracle_defined: int = 0

    evidence_complete: bool = False
    evidence_failed: bool = False

    extra: dict = field(default_factory=dict)


def classify(input_: DecisionInput) -> str:
    """Return the single frozen Outcome per the strict-order decision table."""
    # 1. Environment hard error wins over everything (cannot be a business result).
    if input_.env_hard_error:
        return Outcome.ENV_FAIL.value

    # 2. Data error is an environment/data problem, not a business failure.
    if input_.data_error:
        return Outcome.DATA_FAIL.value

    # 3. Runtime / automation error before the business oracle is reached.
    if input_.automation_error:
        return Outcome.AUTOMATION_FAIL.value

    # 4. Assertion evaluator error (e.g. operator unsupported) is a tooling error.
    if input_.assertion_evaluator_error:
        return Outcome.ASSERTION_ERROR.value

    # 5. A required oracle that FAILED is a real business failure.
    if input_.required_oracle_fail > 0:
        return Outcome.BUSINESS_FAIL.value

    # 6. A required oracle that could not be evaluated is NOT a pass.
    if input_.required_oracle_not_evaluated > 0:
        return Outcome.INCONCLUSIVE.value

    # 7. Every required oracle PASSes AND required evidence is complete -> PASS.
    if (
        input_.required_oracle_defined > 0
        and input_.required_oracle_pass == input_.required_oracle_defined
        and input_.evidence_complete
        and not input_.evidence_failed
    ):
        return Outcome.PASS.value

    # 8. All else is INCONCLUSIVE (never a silent PASS).
    return Outcome.INCONCLUSIVE.value


def compute_run_trust(assertions: list) -> str:
    """TRUST-007: the trust level of a Run's assertions.

    A run is ``TRUSTED`` only when every AssertionResult is bound to a real
    TestOracle (``oracle_source_type == TEST_ORACLE`` / trust_status ``TRUSTED``).
    Any legacy (v1.x CommandPlan assert / historical) or invalid assertion degrades
    the run to ``LEGACY_UNVERIFIED`` so a ``PASS`` can never silently claim a
    Trusted Release Gate. A run with no assertions is ``LEGACY_UNVERIFIED``.
    """
    if not assertions:
        return AssertionTrustStatus.LEGACY_UNVERIFIED.value
    if any(
        getattr(a, "trust_status", None) == AssertionTrustStatus.INVALID.value
        for a in assertions
    ):
        return AssertionTrustStatus.INVALID.value
    all_trusted = all(
        getattr(a, "oracle_source_type", None) == "TEST_ORACLE"
        and getattr(a, "trust_status", None) == AssertionTrustStatus.TRUSTED.value
        for a in assertions
    )
    return (
        AssertionTrustStatus.TRUSTED.value
        if all_trusted
        else AssertionTrustStatus.LEGACY_UNVERIFIED.value
    )
