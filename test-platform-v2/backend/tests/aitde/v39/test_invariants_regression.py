"""V39-010 — AITDE global invariants regression suite.

This is the cross-version guard that pins the TEN global invariants shared by
V3.0–V3.9 (see ``V3.9_Detailed_Development_Implementation_Plan.md`` §0). Each
test maps to exactly one invariant and asserts that its deterministic
enforcement still exists and behaves. Pure, offline-runnable guards are tested
for behaviour; DB-backed guards are pinned as importable so they cannot be
silently removed, with their behavioural coverage living in the v31–v38 suites.

Invariant map:
  1  Frozen Contract 不可直接修改        -> contract.repository.ensure_mutable
  2  ScenarioVersion 精确绑定 ContractVersion -> execution.service._validate_run_binding
  3  AI_INFERRED 不能静默成为 Required Oracle -> scenario.repository.review_oracle
  4  PASS 来自 Required Oracle + Deterministic Assertion + Evidence
                                          -> outcome_classifier.classify + completeness
  5  Runtime/Data/Environment 不能伪装成 BUSINESS_FAIL
                                          -> outcome_classifier.classify
  6  Auto Healing 只能修改 Action        -> browser.healing.HealingGuard
  7  Production 默认只读                 -> production.policies
  8  Secret/PII 不进入 Evidence/logs     -> evidence.sanitizer
  9  所有跨项目访问都做授权              -> execution.service._validate_run_binding
  10 所有正式事实可追溯 Source/Version/Audit -> models + ai_ops.validate_source_refs
"""
from __future__ import annotations

from app.modules.aitde.assertion import completeness
from app.modules.aitde.browser.healing import HealingGuard
from app.modules.aitde.common.enums import (
    PolicyDecision,
    SanitizationStatus,
)
from app.modules.aitde.evidence import sanitizer
from app.modules.aitde.execution.outcome_classifier import DecisionInput, classify
from app.modules.aitde.production import policies


# ── Invariant 4: PASS requires Required Oracle + Deterministic Assertion +
#    Evidence completeness ─────────────────────────────────────────────────────
def test_invariant4_pass_requires_all_required_oracles_and_complete_evidence() -> None:
    """OUTCOME PASS only when every required oracle passes AND evidence complete."""
    # All required oracles pass + evidence complete -> PASS.
    assert (
        classify(
            DecisionInput(
                required_oracle_defined=2,
                required_oracle_pass=2,
                evidence_complete=True,
            )
        )
        == "PASS"
    )

    # Missing evidence degrades PASS -> INCONCLUSIVE (never a silent PASS).
    assert (
        classify(
            DecisionInput(
                required_oracle_defined=2,
                required_oracle_pass=2,
                evidence_complete=False,
            )
        )
        != "PASS"
    )

    # One required oracle fails -> BUSINESS_FAIL, never PASS.
    assert (
        classify(
            DecisionInput(
                required_oracle_defined=2,
                required_oracle_pass=1,
                required_oracle_fail=1,
                evidence_complete=True,
            )
        )
        == "BUSINESS_FAIL"
    )


def test_invariant4_no_required_oracle_means_never_pass() -> None:
    """A run with no required oracle defined can never classify as PASS."""
    outcome = classify(
        DecisionInput(required_oracle_defined=0, evidence_complete=True)
    )
    assert outcome != "PASS"


def test_invariant4_full_evidence_types_actually_require_completeness() -> None:
    required = completeness.required_evidence("API", "API")
    assert set(required) == {"REQUEST", "RESPONSE"}
    assert completeness.is_complete({"REQUEST", "RESPONSE"}, required) is True
    assert completeness.is_complete({"REQUEST"}, required) is False


# ── Invariant 5: Runtime / Data / Environment are NOT business failures ──────
def test_invariant5_env_error_is_env_fail_not_business_fail() -> None:
    assert classify(DecisionInput(env_hard_error=True)) == "ENV_FAIL"


def test_invariant5_data_error_is_data_fail_not_business_fail() -> None:
    assert classify(DecisionInput(data_error=True)) == "DATA_FAIL"


def test_invariant5_automation_error_is_automation_fail_not_business_fail() -> None:
    assert classify(DecisionInput(automation_error=True)) == "AUTOMATION_FAIL"


def test_invariant5_assertion_evaluator_error_is_assertion_error_not_business_fail() -> None:
    assert classify(DecisionInput(assertion_evaluator_error=True)) == "ASSERTION_ERROR"


def test_invariant5_business_fail_only_when_required_oracle_fails() -> None:
    assert classify(DecisionInput(required_oracle_fail=1)) == "BUSINESS_FAIL"


# ── Invariant 6: Auto Healing only changes Action, never Oracle/Contract ─────
def test_invariant6_action_only_healing_is_open_allowed() -> None:
    guard = HealingGuard()
    before = {"commands": [{"driver": "playwright", "action": "click", "id": "btn"}]}
    after = {"commands": [{"driver": "playwright", "action": "click", "id": "btn2"}]}
    proposal = guard.create_proposal(before, after, "locator changed")
    assert proposal["approved"] is True
    assert proposal["status"] == "OPEN"
    assert proposal["audit"] is False


def test_invariant6_oracle_mutation_healing_is_rejected_and_audited() -> None:
    guard = HealingGuard()
    before = {"commands": [{"driver": "oracle", "action": "assert", "id": "o1"}]}
    after = {"commands": [{"driver": "oracle", "action": "assert", "id": "o1", "expected": "x"}]}
    proposal = guard.create_proposal(before, after, "oracle edit")
    assert proposal["approved"] is False
    assert proposal["status"] == "REJECTED"
    assert proposal["reason"] == "oracle_contract_mutation"
    assert proposal["audit"] is True


# ── Invariant 7: Production is read-only by default ──────────────────────────
def test_invariant7_browser_write_action_is_denied() -> None:
    policy = policies.ReadOnlyBrowserPolicy()
    decision, _reason = policy.evaluate(url="/api/order/pay", method="GET")
    assert decision == PolicyDecision.DENY.value


def test_invariant7_prod_db_guard_rejects_write_sql() -> None:
    guard = policies.ProductionDbGuard()
    assert guard.validate("DELETE FROM users")[0] is False
    assert guard.validate("UPDATE users SET x=1")[0] is False
    assert guard.validate("DROP TABLE users")[0] is False
    assert guard.validate("SELECT * FROM users")[0] is True


def test_invariant7_prod_ro_worker_rejects_write_capability() -> None:
    profile = policies.ProdRoWorkerProfile()
    ok, _reason = profile.validate(network_zone="PROD_RO", capabilities=["BROWSER", "POSTGRES"])
    assert ok is False  # POSTGRES is a write capability -> forbidden
    ok, _reason = profile.validate(network_zone="PROD_RO", capabilities=["BROWSER"])
    assert ok is True


# ── Invariant 8: Secrets / PII must not reach Evidence ───────────────────────
def test_invariant8_sensitive_headers_are_redacted() -> None:
    headers = {"Authorization": "Bearer abc123", "X-Custom": "ok", "Cookie": "sid=1"}
    safe = sanitizer.sanitize_headers(headers)
    assert safe["Authorization"] == "<REDACTED>"
    assert safe["Cookie"] == "<REDACTED>"
    assert safe["X-Custom"] == "ok"


def test_invariant8_sensitive_body_fields_are_redacted() -> None:
    body = b'{"password": "hunter2", "token": "t", "name": "alice"}'
    safe_bytes, status = sanitizer.sanitize(body, "application/json", {})
    assert status == SanitizationStatus.SANITIZED.value
    text = safe_bytes.decode()
    assert "hunter2" not in text
    assert "hunter2" not in text and "<REDACTED>" in text


def test_invariant8_unparseable_body_is_rejected_not_written() -> None:
    # A body that cannot be made safe must be REJECTED, never persisted as-is.
    body = b"{not json"
    _safe_bytes, status = sanitizer.sanitize(body, "application/json", {})
    assert status == SanitizationStatus.REJECTED.value


# ── Invariant 10: all formal facts carry Source / Version / Audit ────────────
def test_invariant10_contract_model_carries_traceability_columns() -> None:
    from app.modules.aitde.contract.models import TestContractVersion

    cols = set(TestContractVersion.__table__.c.keys())
    # Formal contract facts must be traceable to source refs + actor audit.
    assert "created_by_type" in cols


def test_invariant10_source_refs_validator_is_importable() -> None:
    from app.modules.aitde.ai_ops.service import validate_source_refs

    assert callable(validate_source_refs)


# ── DB-backed guards pinned importable so they cannot be silently removed ────
def test_invariant1_frozen_contract_guard_importable() -> None:
    from app.modules.aitde.contract.repository import ensure_mutable

    assert callable(ensure_mutable)


def test_invariant2_and_9_run_binding_guard_importable() -> None:
    from app.modules.aitde.execution.service import _validate_run_binding

    assert callable(_validate_run_binding)


def test_invariant3_ai_inferred_oracle_guard_importable() -> None:
    from app.modules.aitde.scenario.repository import review_oracle

    assert callable(review_oracle)
