"""DataRequirement derivation tests (V32-002).

Derivation is deterministic (rule-based) from a scenario version's Given /
Expected business state. The derived candidate must be business-only — never SQL.
"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.data import service
from app.modules.aitde.data.schemas import DataRequirementUpdate
from app.modules.aitde.scenario.models import (
    TestScenarioVersion as ScenarioVersion,
)


def _make_scenario_version(db, given, expected):
    version = ScenarioVersion(
        scenario_id=1,
        version_no=1,
        contract_version_id=1,
        title="可续费",
        given_model_json=json.dumps(given, ensure_ascii=False),
        expected_state_json=json.dumps(expected, ensure_ascii=False),
    )
    db.add(version)
    db.flush()
    return version


def test_derive_business_requirements_from_given_expected(db):
    version = _make_scenario_version(
        db,
        given={"user.status": "normal", "membership.status": "expired"},
        expected={"membership.status": "active"},
    )
    rows = service.derive_data_requirements(db, version.id)
    by_key = {r.requirement_key: r for r in rows}

    # One requirement per business entity, never a SQL statement.
    assert "data-user" in by_key
    assert "data-membership" in by_key
    user = by_key["data-user"]
    assert user.entity_type == "user"
    assert json.loads(user.constraints_json) == {"status": "normal"}
    member = by_key["data-membership"]
    # membership appears in both given + expected; expected value wins for the field.
    assert json.loads(member.constraints_json)["status"] == "active"
    assert "SELECT" not in user.constraints_json
    assert "UPDATE" not in user.constraints_json


def test_derive_is_idempotent(db):
    version = _make_scenario_version(
        db, given={"user.status": "normal"}, expected={}
    )
    service.derive_data_requirements(db, version.id)
    count_after_first = len(service.list_data_requirements(db, version.id))
    service.derive_data_requirements(db, version.id)
    assert len(service.list_data_requirements(db, version.id)) == count_after_first


def test_derive_unknown_scenario_version_rejected(db):
    with pytest.raises(APIException) as exc:
        service.derive_data_requirements(db, 9999)
    assert exc.value.http_status == 404


def test_update_requirement_revise_constraints(db):
    version = _make_scenario_version(
        db, given={"user.status": "normal"}, expected={}
    )
    rows = service.derive_data_requirements(db, version.id)
    target = next(r for r in rows if r.entity_type == "user")
    updated = service.update_data_requirement(
        db,
        target.id,
        DataRequirementUpdate(entity_type="member", constraints={"status": "EXPIRED"}),
    )
    assert updated.entity_type == "member"
    assert json.loads(updated.constraints_json) == {"status": "EXPIRED"}


def test_update_missing_requirement_rejected(db):
    with pytest.raises(APIException) as exc:
        service.update_data_requirement(db, 9999, DataRequirementUpdate())
    assert exc.value.http_status == 404
