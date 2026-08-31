"""V3.9-R1 TRUST-001 / TRUST-002 — Oracle single-source reality tests.

Verifies that a CommandPlan v2 declares observations only, that the Runtime loads
the *real* TestOracle (never a plan-side expected), that AssertionResult binds the
real ``test_oracle_id``, and that v1.x ``asserts`` are flagged LEGACY_UNVERIFIED so
they never count toward a Trusted Release Gate.
"""
from __future__ import annotations

import json

import pytest

from app.modules.aitde.assertion.engine import AssertionEngine
from app.modules.aitde.common.enums import (
    AssertionTrustStatus,
    OracleBindingType,
    OracleSourceType,
)
from app.modules.aitde.execution.models import ExecutionStep
from app.modules.aitde.scenario.models import ScenarioOracleBinding
from app.modules.aitde.workflow.oracle_engine import (
    evaluate_oracles,
    load_bindings,
    load_required_oracles,
    parse_command_plan,
    resolve_observation,
)


def _add_step(db, run, step_key, status=200, body=None):
    step = ExecutionStep(
        run_id=run.id,
        sequence=1,
        step_key=step_key,
        step_type="API",
        status="SUCCEEDED",
        input_snapshot_json="{}",
        output_snapshot_json=json.dumps({"status": status, "body": body or {}}),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def _add_binding(db, run, oracle, binding_type, step_key, selector):
    binding = ScenarioOracleBinding(
        project_id=run.project_id,
        scenario_adapter_id=run.adapter_id,
        scenario_version_id=run.scenario_version_id,
        oracle_id=oracle.id,
        binding_type=binding_type,
        source_step_key=step_key,
        observation_selector_json=json.dumps(selector),
        status="ACTIVE",
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    return binding


# ── parse_command_plan ────────────────────────────────────────────────────────


def test_parse_command_plan_v2_has_no_asserts_or_expected() -> None:
    plan = {"schema_version": "2.0", "commands": [{"id": "renew", "observations": [{"key": "s", "type": "HTTP_STATUS"}]}]}
    desc = parse_command_plan(plan)
    assert desc["is_v2"] is True
    # CommandPlan v2 must never carry business expected via asserts.
    assert "asserts" not in plan["commands"][0]
    assert all("expected" not in c for c in plan["commands"])
    assert len(desc["observations"]) == 1


def test_parse_command_plan_v1_is_legacy() -> None:
    plan = {"version": "1.0", "steps": [{"name": "s", "asserts": [{"kind": "status", "expected": 200}]}]}
    desc = parse_command_plan(plan)
    assert desc["is_v2"] is False
    assert desc["schema_version"] == "1.x"
    assert len(desc["legacy_steps"]) == 1
    assert desc["legacy_steps"][0]["asserts"][0]["expected"] == 200


# ── load_required_oracles / load_bindings ────────────────────────────────────


def test_load_required_oracles_returns_real_oracle(db, run_graph) -> None:
    oracles = load_required_oracles(db, run_graph["scenario_version"].id)
    assert len(oracles) == 1
    assert oracles[0].id == run_graph["oracle"].id


def test_load_bindings_filters_by_adapter(scenario_run_with_binding) -> None:
    bindings = load_bindings(
        scenario_run_with_binding["db"],
        scenario_run_with_binding["run"].adapter_id,
        scenario_run_with_binding["run"].scenario_version_id,
    )
    assert len(bindings) == 1


# ── resolve_observation ──────────────────────────────────────────────────────


def test_resolve_observation_api_jsonpath(db, run_graph) -> None:
    run = run_graph["run"]
    _add_step(db, run, "renew-response", status=200, body={"data": {"membership": {"status": "ACTIVE"}}})
    binding = _add_binding(
        db, run, run_graph["oracle"], OracleBindingType.API_JSONPATH.value,
        "renew-response", {"jsonpath": "$.data.membership.status"},
    )
    from app.modules.aitde.execution import repository

    steps = repository.list_steps(db, run.id, run_graph["project_id"])
    actual = resolve_observation(binding, steps)
    assert actual == "ACTIVE"


def test_resolve_observation_missing_step_returns_none(db, run_graph) -> None:
    run = run_graph["run"]
    binding = _add_binding(
        db, run, run_graph["oracle"], OracleBindingType.API_JSONPATH.value,
        "does-not-exist", {"jsonpath": "$.data.status"},
    )
    actual = resolve_observation(binding, [])
    assert actual is None


# ── evaluate_oracles v2 → trusted ────────────────────────────────────────────


def test_evaluate_oracles_v2_binds_real_test_oracle(db, run_graph) -> None:
    run = run_graph["run"]
    oracle = run_graph["oracle"]
    _add_step(db, run, "renew-response", status=200, body={"data": {"membership": {"status": "ACTIVE"}}})
    _add_binding(
        db, run, oracle, OracleBindingType.API_JSONPATH.value,
        "renew-response", {"jsonpath": "$.data.membership.status"},
    )

    result = evaluate_oracles(db, run, run_graph["project_id"])

    assert result["oracle_total"] == 1
    assert result["trust_level"] == AssertionTrustStatus.TRUSTED.value
    assert result["pass"] == 1
    a = result["assertions"][0]
    assert a["test_oracle_id"] == oracle.id
    assert a["trust_status"] == AssertionTrustStatus.TRUSTED.value

    from app.modules.aitde.execution import repository

    rows = repository.list_assertions(db, run.id, run_graph["project_id"])
    assert rows[0].test_oracle_id == oracle.id
    assert rows[0].oracle_source_type == OracleSourceType.TEST_ORACLE.value
    assert rows[0].trust_status == AssertionTrustStatus.TRUSTED.value


def test_evaluate_oracles_v2_no_binding_is_not_evaluated(db, run_graph) -> None:
    run = run_graph["run"]
    _add_step(db, run, "renew-response", status=200, body={"data": {"membership": {"status": "ACTIVE"}}})

    result = evaluate_oracles(db, run, run_graph["project_id"])

    # No binding -> actual missing -> NOT_EVALUATED, never PASS.
    assert result["pass"] == 0
    assert result["not_evaluated"] == 1
    assert result["assertions"][0]["result"] == "NOT_EVALUATED"


def test_evaluate_oracles_v1_is_legacy_untrusted(db, run_graph) -> None:
    run = run_graph["run"]
    # Rewrite the plan as v1.x so the legacy path runs.
    from app.modules.aitde.command.models import CommandPlanVersion

    pv = run_graph["plan_version"]
    pv.schema_version = "1.0"
    pv.plan_json = json.dumps(
        {
            "version": "1.0",
            "steps": [{"name": "renew", "asserts": [{"kind": "status", "expected": 200}]}],
        }
    )
    db.commit()

    result = evaluate_oracles(db, run, run_graph["project_id"])

    assert result["trust_level"] == AssertionTrustStatus.LEGACY_UNVERIFIED.value
    assert result["assertions"][0]["test_oracle_id"] is None
    assert result["assertions"][0]["trust_status"] == AssertionTrustStatus.LEGACY_UNVERIFIED.value


@pytest.fixture
def scenario_run_with_binding(run_graph, db):
    """run_graph + a step + an API_JSONPATH binding exposed for binding tests."""
    run = run_graph["run"]
    _add_step(db, run, "renew-response", status=200, body={"data": {"membership": {"status": "ACTIVE"}}})
    _add_binding(
        db, run, run_graph["oracle"], OracleBindingType.API_JSONPATH.value,
        "renew-response", {"jsonpath": "$.data.membership.status"},
    )
    return {"db": db, "run": run, "oracle": run_graph["oracle"]}
