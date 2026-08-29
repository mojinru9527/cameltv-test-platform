"""Shared AITDE V3.1 unit-test fixtures (in-memory SQLite)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde import contract, execution, mission, scenario  # noqa: F401  registers tables


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
def scenario_graph(db):
    """A project-1 Mission + ContractVersion + ScenarioVersion used to bind runs."""
    from app.modules.aitde.common.enums import ContractVersionStatus
    from app.modules.aitde.contract.models import TestContractVersion
    from app.modules.aitde.mission.models import Mission
    from app.modules.aitde.scenario.models import (
        TestScenario,
        TestScenarioVersion,
    )

    mission = Mission(project_id=1, title="成员中心 V3.1", created_by=9)
    db.add(mission)
    db.flush()

    contract_version = TestContractVersion(
        contract_id=1, version_no=1, status=ContractVersionStatus.FROZEN.value
    )
    db.add(contract_version)
    db.flush()

    scenario = TestScenario(project_id=1, mission_id=mission.id, scenario_key="SC-001")
    db.add(scenario)
    db.flush()

    scenario_version = TestScenarioVersion(
        scenario_id=scenario.id,
        version_no=1,
        contract_version_id=contract_version.id,
        title="可登录",
    )
    db.add(scenario_version)
    db.commit()
    return {
        "mission": mission,
        "contract_version": contract_version,
        "scenario": scenario,
        "scenario_version": scenario_version,
    }
