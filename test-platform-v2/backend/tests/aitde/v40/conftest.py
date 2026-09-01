"""Shared AITDE V4.0 unit-test fixtures (in-memory SQLite)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
import app.models  # noqa: F401  registers all models
import app.modules.aitde.legacy_cutover.models  # noqa: F401
import app.modules.aitde.scenario.models  # noqa: F401  # test_scenarios for V40-005 promote
import app.modules.aitde.data.models  # noqa: F401  # legacy_dataset_links for V40-007
import app.modules.aitde.governance.models  # noqa: F401  # V40-009..020 enterprise tables
import app.modules.aitde.mission.models  # noqa: F401  # missions for V40-020 report
import app.modules.aitde.contract.models  # noqa: F401  # contract for V40-020 report
import app.modules.aitde.execution.models  # noqa: F401  # execution_runs for V40-020 report


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
