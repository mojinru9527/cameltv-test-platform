"""Shared AITDE V3.6 unit-test fixtures (in-memory SQLite)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
import app.models  # noqa: F401  registers all tables incl. production_evidence
import app.modules.aitde.data.models  # noqa: F401  registers data_fixtures/fixture_entities
import app.modules.aitde.scenario.models  # noqa: F401
import app.modules.aitde.mission.models  # noqa: F401
import app.modules.aitde.contract.models  # noqa: F401


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
