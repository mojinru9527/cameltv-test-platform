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
    TestOracle as OracleModel,
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


def test_derive_from_oracle_expected_value(db):
    """Oracle target.entity + expected_value derives a requirement for that entity."""
    version = _make_scenario_version(db, given={"state": "precondition"}, expected={})
    oracle = OracleModel(
        scenario_version_id=version.id, oracle_key="membership-active",
        oracle_type="DB", target_json=json.dumps({"entity": "membership"}),
        operator="eq", expected_value_json=json.dumps({"status": "active"}), required=True,
    )
    db.add(oracle)
    db.flush()
    rows = service.derive_data_requirements(db, version.id)
    by_key = {r.requirement_key: r for r in rows}
    assert "data-membership" in by_key
    member = by_key["data-membership"]
    assert json.loads(member.constraints_json) == {"status": "active"}
    assert "oracle_ids" in member.source_refs_json


def test_derive_ignores_non_dotted_state_key(db):
    """A scalar key without an entity prefix (e.g. 'state') yields no requirement."""
    version = _make_scenario_version(
        db, given={"state": "precondition"}, expected={"state": "active"}
    )
    rows = service.derive_data_requirements(db, version.id)
    assert rows == []


def test_derive_malformed_oracle_ignored(db):
    """Malformed oracle target/expected is skipped rather than crashing the derive."""
    version = _make_scenario_version(db, given={"user.status": "normal"}, expected={})
    oracle = OracleModel(
        scenario_version_id=version.id, oracle_key="bad", oracle_type="DB",
        target_json="not-json", expected_value_json="not-json", required=True,
    )
    db.add(oracle)
    db.flush()
    rows = service.derive_data_requirements(db, version.id)
    by_key = {r.requirement_key: r for r in rows}
    assert "data-user" in by_key
    assert len(rows) == 1


def test_derive_merges_oracle_with_given_entity(db):
    """Oracle constraints enrich an entity already present in Given."""
    version = _make_scenario_version(
        db, given={"membership.status": "expired"}, expected={}
    )
    oracle = OracleModel(
        scenario_version_id=version.id, oracle_key="m", oracle_type="DB",
        target_json=json.dumps({"entity": "membership"}),
        operator="eq", expected_value_json=json.dumps({"status": "active"}), required=True,
    )
    db.add(oracle)
    db.flush()
    rows = service.derive_data_requirements(db, version.id)
    member = next(r for r in rows if r.entity_type == "membership")
    constraints = json.loads(member.constraints_json)
    # given value + oracle expected value both surface (oracle wins for shared field)
    assert constraints["status"] == "active"
