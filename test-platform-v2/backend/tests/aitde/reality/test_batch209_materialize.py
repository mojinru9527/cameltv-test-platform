"""Batch 209 (C2) — auto-materialize oracle bindings on plan approve."""
from __future__ import annotations

import json

from app.modules.aitde.command import service as command_service
from app.modules.aitde.command.models import CommandPlanVersion
from app.modules.aitde.common.enums import ReviewStatus
from app.modules.aitde.scenario import repository as scenario_repo
from app.modules.aitde.scenario.models import (
    ScenarioOracleBinding as _Binding,
    TestOracle as _Oracle,
)


def _oracle(db, scenario_version_id: int) -> _Oracle:
    row = _Oracle(
        scenario_version_id=scenario_version_id,
        oracle_key="renew.membership.status",
        oracle_type="API",
        target_json=json.dumps({"jsonpath": "$.data.status"}),
        operator="eq",
        expected_value_json='"ACTIVE"',
        required=True,
        review_status=ReviewStatus.APPROVED.value,
    )
    db.add(row)
    db.flush()
    return row


def _plan(db, scenario_version_id: int, status: str = "DRAFT") -> CommandPlanVersion:
    plan = CommandPlanVersion(
        command_plan_id=1,
        version_no=1,
        scenario_version_id=scenario_version_id,
        contract_version_id=0,
        schema_version="2.0",
        status=status,
        plan_json=json.dumps(
            {
                "schema_version": "2.0",
                "base_url": "http://svc.test",
                "commands": [
                    {
                        "id": "renew",
                        "driver": "api",
                        "action": "request",
                        "input": {"method": "POST", "path": "/renew"},
                        "observations": [
                            {
                                "key": "renew.membership.status",
                                "type": "HTTP_RESPONSE",
                            }
                        ],
                    }
                ],
            }
        ),
        generated_by_type="PLANNER",
    )
    db.add(plan)
    db.flush()
    return plan


def test_materialize_bindings_is_idempotent(db):
    plan = _plan(db, 1)
    oracle = _oracle(db, 1)
    db.commit()

    first = scenario_repo.materialize_bindings_for_plan(db, plan.id)
    assert first["created"] == 1
    binding = db.query(_Binding).filter_by(oracle_id=oracle.id).first()
    assert binding is not None
    assert binding.binding_type == "API_JSONPATH"
    assert binding.source_step_key == "renew"
    assert binding.status == "ACTIVE"

    second = scenario_repo.materialize_bindings_for_plan(db, plan.id)
    assert second["created"] == 0
    assert db.query(_Binding).filter_by(oracle_id=oracle.id).count() == 1


def test_approve_version_materializes_binding(db):
    plan = _plan(db, 7)
    oracle = _oracle(db, 7)
    db.commit()

    approved = command_service.approve_version(db, plan.id, user_id=9)
    assert approved.status == "VALIDATED"
    binding = db.query(_Binding).filter_by(oracle_id=oracle.id).first()
    assert binding is not None
    assert binding.status == "ACTIVE"


def test_unmatched_oracle_stays_unbound(db):
    plan = _plan(db, 9)
    oracle = _Oracle(
        scenario_version_id=9,
        oracle_key="other.oracle",
        oracle_type="DB",
        target_json="{}",
        operator="eq",
        expected_value_json='"x"',
        required=True,
        review_status=ReviewStatus.APPROVED.value,
    )
    db.add(oracle)
    db.commit()

    out = scenario_repo.materialize_bindings_for_plan(db, plan.id)
    assert out["created"] == 0
    assert db.query(_Binding).filter_by(oracle_id=oracle.id).count() == 0
