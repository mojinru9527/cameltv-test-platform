"""Shared AITDE V3.2 unit-test fixtures (in-memory SQLite)."""
from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
import app.models.environment  # noqa: F401  registers environment table
import app.models.dataset  # noqa: F401  registers dataset table
from app.modules.aitde.data import service  # noqa: F401  registers data_sources table
import app.modules.aitde.scenario.models  # noqa: F401  registers scenario tables
import app.modules.aitde.mission.models  # noqa: F401  registers mission tables
import app.modules.aitde.contract.models  # noqa: F401  registers contract tables
import app.modules.aitde.execution.models  # noqa: F401  registers execution tables

from app.modules.aitde.drivers.database.base import DatabaseDriver


class UserSqliteDriver(DatabaseDriver):
    """Real sqlite DataSource driver backing DB_FIXTURE provisioning in tests."""

    source_type = "SQLITE"

    def build_url(self) -> str:
        return f"sqlite:///{self.config['db_path']}"


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
def patched_db_driver(monkeypatch):
    """Patch build_data_driver to a REAL sqlite source so provisioning executes.

    V3.9-R2 (DATA-002) makes provisioning a real physical effect + verify; these
    legacy V32 fixtures must therefore back the DataSource with a real DB rather
    than rely on the recipe-only behaviour the reality gate removes.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE user (id INTEGER PRIMARY KEY, status TEXT)"))
    engine.dispose()
    driver = UserSqliteDriver({"db_path": path, "table_allowlist": ["user"]}, "ref")
    monkeypatch.setattr(
        "app.modules.aitde.data.executors.data_plan_executor.build_data_driver",
        lambda s: driver,
    )
    try:
        yield driver
    finally:
        os.remove(path)


@pytest.fixture()
def ready_fixture(db, patched_db_driver):
    """A READY fixture produced from a scenario version + readonly source."""
    import json as _json

    from app.modules.aitde.data import fixture_service
    from app.modules.aitde.data.models import DataSource
    from app.modules.aitde.data.schemas import DataPlanGenerateRequest
    from app.modules.aitde.scenario.models import (
        TestScenarioVersion as ScenarioVersion,
    )

    version = ScenarioVersion(
        scenario_id=1,
        version_no=1,
        contract_version_id=1,
        title="t",
        given_model_json=_json.dumps({"user.status": "normal"}, ensure_ascii=False),
        expected_state_json="{}",
    )
    db.add(version)
    db.flush()

    source = DataSource(
        project_id=1, source_type="MYSQL", name="db",
        access_mode="READWRITE",
        config_json=_json.dumps({"table_allowlist": ["user"]}, ensure_ascii=False),
        created_by=9,
    )
    db.add(source)
    db.flush()

    service.derive_data_requirements(db, version.id)
    plan = service.generate_data_plan(db, version.id, None, 1, DataPlanGenerateRequest())
    db.flush()
    fixture = fixture_service.provision_fixture(db, plan, source, None, 1)
    return {"version": version, "source": source, "plan": plan, "fixture": fixture}
