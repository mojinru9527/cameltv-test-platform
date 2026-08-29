"""DataPlan / Step tests (V32-003).

Verifies the planner: deterministic plan_hash, strategy selection by available
data sources, production write policy rejection, and approval.
"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.models.environment import Environment
from app.modules.aitde.data import service
from app.modules.aitde.data.models import DataSource
from app.modules.aitde.data.schemas import DataPlanGenerateRequest
from app.modules.aitde.scenario.models import TestScenarioVersion as ScenarioVersion


def _scenario_version(db, given):
    version = ScenarioVersion(
        scenario_id=1,
        version_no=1,
        contract_version_id=1,
        title="t",
        given_model_json=json.dumps(given, ensure_ascii=False),
        expected_state_json="{}",
    )
    db.add(version)
    db.flush()
    return version


def _data_source(db, access_mode, env_id=None, source_type="POSTGRES"):
    ds = DataSource(
        project_id=1,
        source_type=source_type,
        name="db",
        access_mode=access_mode,
        environment_id=env_id,
        created_by=9,
    )
    db.add(ds)
    db.flush()
    return ds


def test_generate_plan_stable_hash(db):
    version = _scenario_version(db, given={"user.status": "normal"})
    p1 = service.generate_data_plan(
        db, version.id, None, 1, DataPlanGenerateRequest()
    )
    p2 = service.generate_data_plan(
        db, version.id, None, 1, DataPlanGenerateRequest()
    )
    assert p1.plan_hash == p2.plan_hash
    steps = service.to_plan_dict(db, p1)["steps"]
    assert len(steps) >= 1
    assert steps[0]["status"] == "PENDING"


def test_strategy_db_fixture_when_readwrite_source(db):
    version = _scenario_version(db, given={"user.status": "normal"})
    _data_source(db, access_mode="READWRITE")
    plan = service.generate_data_plan(
        db, version.id, None, 1, DataPlanGenerateRequest()
    )
    assert plan.strategy == "DB_FIXTURE"
    assert plan.risk_level == "P1"


def test_strategy_existing_when_readonly_source(db):
    version = _scenario_version(db, given={"user.status": "normal"})
    _data_source(db, access_mode="READONLY")
    plan = service.generate_data_plan(
        db, version.id, None, 1, DataPlanGenerateRequest()
    )
    assert plan.strategy == "EXISTING"
    assert plan.risk_level == "P2"


def test_write_strategy_on_prod_rejected(db):
    env = Environment(project_id=1, name="prod", env_type="prod", is_production=True)
    db.add(env)
    db.flush()
    version = _scenario_version(db, given={"user.status": "normal"})
    _data_source(db, access_mode="READWRITE", env_id=env.id)
    with pytest.raises(APIException) as exc:
        service.generate_data_plan(
            db, version.id, env.id, 1, DataPlanGenerateRequest()
        )
    assert exc.value.http_status == 400
    assert "生产环境" in exc.value.msg


def test_approve_plan(db):
    version = _scenario_version(db, given={"user.status": "normal"})
    plan = service.generate_data_plan(
        db, version.id, None, 1, DataPlanGenerateRequest()
    )
    approved = service.approve_data_plan(db, plan.id, 9)
    assert approved.status == "APPROVED"
    assert approved.approved_by == 9


def test_generate_plan_missing_scenario_rejected(db):
    with pytest.raises(APIException) as exc:
        service.generate_data_plan(db, 9999, None, 1, DataPlanGenerateRequest())
    assert exc.value.http_status == 404
