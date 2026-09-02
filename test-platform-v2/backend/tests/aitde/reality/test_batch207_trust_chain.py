"""Batch 207 — trusted-chain reality tests.

Server-side ActionPlanner generation, explicit human oracle promotion, the
oracle-binding producer, and fail-fast run readiness.
"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.command import DEFAULT_REGISTRY, service as command_service
from app.modules.aitde.common.enums import ReviewStatus
from app.modules.aitde.scenario import repository as scenario_repo
from app.modules.aitde.scenario import service as scenario_service
from app.modules.aitde.scenario.models import TestOracle as _TestOracle
from app.modules.aitde.scenario.schemas import OracleBindingCreate


def test_plan_from_scenario_returns_valid_command_ir(db, run_graph):
    ir = command_service.plan_from_scenario(
        db, run_graph["scenario_version"].id, route="/member"
    )
    assert ir["schema_version"] == "1.0"
    assert DEFAULT_REGISTRY.validate(ir) == []
    drivers = {c["driver"] for c in ir["commands"]}
    assert "browser" in drivers
    # every frozen oracle becomes an assertion command
    assert any(
        c.get("driver") == "assertion"
        and (c.get("input") or {}).get("oracle_key") == "renew.membership.status"
        for c in ir["commands"]
    )


def test_review_oracle_promote_requires_explicit_flag(db, run_graph):
    sv = run_graph["scenario_version"].id
    ai_oracle = _TestOracle(
        scenario_version_id=sv,
        oracle_key="ai.inferred.one",
        oracle_type="DB",
        target_json="{}",
        operator="eq",
        expected_value_json="{}",
        source_type="AI_INFERRED",
        required=False,
    )
    db.add(ai_oracle)
    db.commit()

    # without promote: guard holds (stays PROPOSED)
    kept = scenario_repo.review_oracle(
        db, ai_oracle, ReviewStatus.APPROVED.value, user_id=9, required=True
    )
    assert kept.review_status == ReviewStatus.PROPOSED.value
    assert kept.source_type == "AI_INFERRED"

    # explicit human promote: re-sourced as TESTER_APPROVED + APPROVED
    promoted = scenario_repo.review_oracle(
        db,
        ai_oracle,
        ReviewStatus.APPROVED.value,
        user_id=9,
        required=True,
        promote=True,
    )
    assert promoted.review_status == ReviewStatus.APPROVED.value
    assert promoted.source_type == "TESTER_APPROVED"
    assert promoted.required is True


def test_oracle_binding_producer_and_fail_fast(db, run_graph):
    scenario = run_graph["scenario"]
    sv = run_graph["scenario_version"].id
    oracle = run_graph["oracle"]

    # missing binding -> explicit ORACLE_NOT_BOUND (not silent NOT_EVALUATED)
    from app.modules.aitde.execution import service as exec_service

    data = {
        "scenario_id": scenario.id,
        "scenario_version_id": sv,
        "contract_version_id": run_graph["contract_version"].id,
        "environment_snapshot_id": 1,
        "environment_id": 0,
        "mission_id": run_graph["mission"].id,
    }
    with pytest.raises(APIException) as exc:
        exec_service.create_run(db, data, project_id=1, user_id=9)
    assert exc.value.http_status == 400
    assert "ORACLE_NOT_BOUND" in exc.value.msg

    binding = scenario_service.create_oracle_binding(
        db,
        scenario.id,
        1,
        OracleBindingCreate(
            scenario_version_id=sv,
            oracle_id=oracle.id,
            binding_type="API_JSONPATH",
            source_step_key="renew",
            observation_selector={"jsonpath": "$.data.status"},
            scenario_adapter_id=run_graph["adapter"].id,
        ),
    )
    assert binding["status"] == "ACTIVE"
    listed = scenario_service.list_oracle_bindings(db, scenario.id, 1)
    assert any(b["id"] == binding["id"] for b in listed)

    # idempotent re-create updates in place
    again = scenario_service.create_oracle_binding(
        db,
        scenario.id,
        1,
        OracleBindingCreate(
            scenario_version_id=sv,
            oracle_id=oracle.id,
            binding_type="API_JSONPATH",
            source_step_key="renew",
            observation_selector={"jsonpath": "$.data.status"},
            scenario_adapter_id=run_graph["adapter"].id,
        ),
    )
    assert again["id"] == binding["id"]

    run = exec_service.create_run(db, data, project_id=1, user_id=9)
    assert run.id is not None

    # remove the plan -> PLAN_MISSING
    db.delete(run_graph["plan_version"])
    db.commit()
    with pytest.raises(APIException) as exc2:
        exec_service.create_run(db, data, project_id=1, user_id=9)
    assert "PLAN_MISSING" in exc2.value.msg


def test_binding_must_match_oracle_version(db, run_graph):
    other = _TestOracle(
        scenario_version_id=run_graph["scenario_version"].id + 999,
        oracle_key="x",
        oracle_type="DB",
        target_json="{}",
        operator="eq",
        expected_value_json="{}",
    )
    db.add(other)
    db.commit()
    with pytest.raises(APIException):
        scenario_service.create_oracle_binding(
            db,
            run_graph["scenario"].id,
            1,
            OracleBindingCreate(
                scenario_version_id=run_graph["scenario_version"].id,
                oracle_id=other.id,
                binding_type="API_JSONPATH",
            ),
        )
