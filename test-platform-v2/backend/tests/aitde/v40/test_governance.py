"""AITDE V4.0 (V40-011/012/014/015/017/018) enterprise governance tests."""

from __future__ import annotations

from app.modules.aitde.governance.service import (
    CostLedgerService,
    DrTestService,
    ModelPolicyService,
    PlatformReadinessEvaluator,
    RetentionService,
)


def test_retention_evaluate_lifecycle(db):
    r = RetentionService
    r.upsert(db, 1, "EVIDENCE", "CONFIDENTIAL", retention_days=30)
    assert r.evaluate(db, "EVIDENCE", "CONFIDENTIAL", 10)["action"] == "ARCHIVE"
    assert r.evaluate(db, "EVIDENCE", "CONFIDENTIAL", 40)["action"] == "DELETE"
    # No policy -> KEEP.
    assert r.evaluate(db, "LOG", "RESTRICTED", 999)["action"] == "KEEP"


def test_model_policy_routing_fail_closed(db):
    m = ModelPolicyService
    m.upsert(db, 1, "PUBLIC", ["deepseek"], ["deepseek-v4"], redaction_required=False)
    assert m.is_allowed(db, "deepseek", "deepseek-v4", "PUBLIC")["allowed"] is True
    assert m.is_allowed(db, "openai", "gpt-4", "PUBLIC")["allowed"] is False
    # Unconfigured sensitive level -> fail closed (no model).
    assert m.is_allowed(db, "deepseek", "deepseek-v4", "RESTRICTED")["allowed"] is False


def test_cost_ledger_and_budget(db):
    c = CostLedgerService
    c.record(db, 1, "SCENARIO_GEN", "deepseek-v4", input_units=100, output_units=50, cost_amount=1.5)
    c.record(db, 1, "TRIAGE", "deepseek-v4", input_units=40, output_units=10, cost_amount=0.5)
    usage = c.project_usage(db, 1)
    assert usage["entries"] == 2
    assert usage["total_cost"] == 2.0
    assert c.check_budget(db, 1, budget=1.0)["budget_exceeded"] is True
    assert c.check_budget(db, 1, budget=5.0)["budget_exceeded"] is False


def test_dr_test_record_and_list(db):
    d = DrTestService
    d.record(db, 1, "BACKUP_RESTORE", "test", "PASS", rto_seconds=120, rpo_seconds=60, evidence_uri="s3://dr/1")
    d.record(db, 1, "TEMPORAL_RECOVERY", "test", "FAIL", rto_seconds=999, rpo_seconds=999)
    rows = d.list(db, 1)
    assert len(rows) == 2
    assert rows[0]["test_type"] == "TEMPORAL_RECOVERY"  # newest first


def test_platform_readiness_gate_pass_and_fail():
    ev = PlatformReadinessEvaluator
    ok = {
        "p0_false_pass_rate": 0.005,
        "false_fail_rate": 0.01,
        "evidence_completeness": 0.995,
        "replay_audit_consistency": 0.995,
        "fixture_cleanup_success": 0.995,
        "prod_unauthorized_write": 0,
        "secret_leakage": 0,
        "pii_leakage": 0,
        "contract_unauthorized_mutation": 0,
        "mission_workflow_adoption": 0.85,
    }
    assert ev.evaluate(ok)["pass"] is True

    bad = dict(ok)
    bad["p0_false_pass_rate"] = 0.02  # exceeds <1%
    bad["prod_unauthorized_write"] = 1
    res = ev.evaluate(bad)
    assert res["pass"] is False
    assert "p0_false_pass_rate" in res["failed"]
    assert "prod_unauthorized_write" in res["failed"]


def test_platform_readiness_gate_missing_metric_fails():
    res = PlatformReadinessEvaluator.evaluate({"p0_false_pass_rate": 0.0})
    assert res["pass"] is False
    missing = [c["metric"] for c in res["checks"] if c.get("reason") == "missing"]
    assert len(missing) > 0
