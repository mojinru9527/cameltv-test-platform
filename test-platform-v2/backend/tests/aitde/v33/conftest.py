"""Shared AITDE V3.3 unit-test fixtures (in-memory SQLite)."""
from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde.command import models  # noqa: F401  registers command tables
from app.modules.aitde.browser import models as browser_models  # noqa: F401  registers browser tables
from app.modules.aitde.manual import models as manual_models  # noqa: F401  registers manual tables
from app.modules.aitde.data import models as data_models  # noqa: F401  registers data tables
from app.modules.aitde.scenario import models as scenario_models  # noqa: F401  registers scenario tables
from app.modules.aitde.mission import models as mission_models  # noqa: F401  registers mission tables
from app.modules.aitde.contract import models as contract_models  # noqa: F401  registers contract tables
from app.modules.aitde.execution import models as execution_models  # noqa: F401  registers execution tables

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
    S = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = S()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def patched_db_driver(monkeypatch):
    """Patch build_data_driver to a REAL sqlite source so provisioning executes.

    V3.9-R2 (DATA-002) makes provisioning a real physical effect + verify; legacy
    V33 fixtures back the DataSource with a real DB instead of the recipe-only
    behaviour the reality gate removes.
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
