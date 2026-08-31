"""Shared AITDE V3.9-R1 Reality Gate test fixtures (in-memory SQLite)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde import (  # noqa: F401  registers tables
    ai_closed_loop,
    command,
    contract,
    continuous,
    execution,
    mission,
    scenario,
    scope,
    smart_regression,
    workflow,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def run_graph(db):
    """A full run graph: mission -> contract -> scenario/version -> adapter -> run.

    Also creates one required TestOracle, a v2 CommandPlanVersion, and returns the
    seeded objects plus an empty ExecutionStep list writer.
    """
    import json

    from app.modules.aitde.command.models import CommandPlan, CommandPlanVersion
    from app.modules.aitde.common.enums import (
        AdapterStatus,
        AdapterType,
        ContractVersionStatus,
        OracleType,
        ReviewStatus,
    )
    from app.modules.aitde.contract.models import TestContractVersion
    from app.modules.aitde.execution.models import ExecutionRun, ScenarioAdapter
    from app.modules.aitde.mission.models import Mission
    from app.modules.aitde.scenario.models import (
        TestOracle,
        TestScenario,
        TestScenarioVersion,
    )

    project_id = 1
    mission = Mission(project_id=project_id, title="V3.9 Reality Gate", created_by=9)
    db.add(mission)
    db.flush()

    contract_version = TestContractVersion(
        contract_id=1, version_no=1, status=ContractVersionStatus.FROZEN.value
    )
    db.add(contract_version)
    db.flush()

    scenario = TestScenario(project_id=project_id, mission_id=mission.id, scenario_key="SC-V39-001")
    db.add(scenario)
    db.flush()

    scenario_version = TestScenarioVersion(
        scenario_id=scenario.id,
        version_no=1,
        contract_version_id=contract_version.id,
        title="续费后会员状态",
    )
    db.add(scenario_version)
    db.flush()

    adapter = ScenarioAdapter(
        scenario_id=scenario.id,
        scenario_version_id=scenario_version.id,
        adapter_type=AdapterType.API.value,
        status=AdapterStatus.VALIDATED.value,
        config_json="{}",
        created_by=9,
    )
    db.add(adapter)
    db.flush()

    plan = CommandPlan(scenario_adapter_id=adapter.id, current_version_no=1)
    db.add(plan)
    db.flush()
    plan_version = CommandPlanVersion(
        command_plan_id=plan.id,
        version_no=1,
        scenario_version_id=scenario_version.id,
        contract_version_id=contract_version.id,
        schema_version="2.0",
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
                            {"key": "renew.http_status", "type": "HTTP_STATUS"},
                            {"key": "renew.response", "type": "HTTP_RESPONSE"},
                        ],
                    }
                ],
            }
        ),
        status="ACTIVE",
        generated_by_type="AI",
    )
    db.add(plan_version)
    db.flush()

    oracle = TestOracle(
        scenario_version_id=scenario_version.id,
        oracle_key="renew.membership.status",
        oracle_type=OracleType.API.value,
        target_json="{}",
        operator="eq",
        expected_value_json='"ACTIVE"',
        required=True,
        review_status=ReviewStatus.APPROVED.value,
    )
    db.add(oracle)
    db.flush()

    run = ExecutionRun(
        project_id=project_id,
        mission_id=mission.id,
        scenario_id=scenario.id,
        scenario_version_id=scenario_version.id,
        contract_version_id=contract_version.id,
        adapter_id=adapter.id,
        environment_id=0,
        created_by=9,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    db.refresh(oracle)
    db.refresh(plan_version)

    return {
        "project_id": project_id,
        "mission": mission,
        "contract_version": contract_version,
        "scenario": scenario,
        "scenario_version": scenario_version,
        "adapter": adapter,
        "plan_version": plan_version,
        "oracle": oracle,
        "run": run,
    }
