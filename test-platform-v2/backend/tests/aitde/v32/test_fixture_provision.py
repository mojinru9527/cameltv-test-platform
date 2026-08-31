"""Fixture provision (POST /api/v2/fixtures) tests (V32-009 补口)."""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.data import fixture_service, repository, service
from app.modules.aitde.data.models import DataSource
from app.modules.aitde.data.schemas import DataPlanGenerateRequest
from app.modules.aitde.scenario.models import TestScenarioVersion as ScenarioVersion


def _scenario_version(db, given):
    v = ScenarioVersion(
        scenario_id=1, version_no=1, contract_version_id=1, title="t",
        given_model_json=json.dumps(given, ensure_ascii=False), expected_state_json="{}",
    )
    db.add(v)
    db.flush()
    return v


def _db_fixture_source(db):
    src = DataSource(
        project_id=1, source_type="MYSQL", name="db", access_mode="READWRITE",
        config_json=json.dumps({"table_allowlist": ["user"]}, ensure_ascii=False),
        created_by=9,
    )
    db.add(src)
    db.flush()
    return src


def _req_plan(db, scenario_version_id):
    service.derive_data_requirements(db, scenario_version_id)
    return service.generate_data_plan(db, scenario_version_id, None, 1, DataPlanGenerateRequest())


def test_provision_db_fixture_approved_plan(db, patched_db_driver):
    version = _scenario_version(db, given={"user.status": "normal"})
    _db_fixture_source(db)
    plan = _req_plan(db, version.id)
    assert plan.strategy == "DB_FIXTURE"
    assert plan.risk_level == "P1"

    service.approve_data_plan(db, plan.id, 9)
    fixture = fixture_service.provision_fixture_from_plan(db, plan.id, 1, None, None)
    assert fixture.status == "READY"
    assert fixture.strategy == "DB_FIXTURE"
    entities = repository.list_fixture_entities(db, fixture.id)
    assert len(entities) >= 1
    assert entities[0].created_by_fixture is True
    assert entities[0].cleanup_action_json is not None
    # V3.9-R2: the entity was really created + verified, not a recipe.
    assert entities[0].verification_status == "VERIFIED"
    assert entities[0].physical_status == "PHYSICAL_CREATED"


def test_provision_high_risk_plan_needs_approval(db):
    version = _scenario_version(db, given={"user.status": "normal"})
    _db_fixture_source(db)
    plan = _req_plan(db, version.id)
    with pytest.raises(APIException) as exc:
        fixture_service.provision_fixture_from_plan(db, plan.id, 1, None, None)
    assert exc.value.http_status == 400
    assert "批准" in exc.value.msg


def test_provision_missing_plan_404(db):
    with pytest.raises(APIException) as exc:
        fixture_service.provision_fixture_from_plan(db, 9999, 1, None, None)
    assert exc.value.http_status == 404


def test_provision_uses_explicit_source_id(db, patched_db_driver):
    version = _scenario_version(db, given={"user.status": "normal"})
    src = _db_fixture_source(db)
    plan = _req_plan(db, version.id)
    service.approve_data_plan(db, plan.id, 9)
    fixture = fixture_service.provision_fixture_from_plan(db, plan.id, 1, None, src.id)
    assert fixture.data_source_id == src.id
    assert fixture.status == "READY"
