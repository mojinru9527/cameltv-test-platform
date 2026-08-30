"""Shared AITDE V3.4 unit-test fixtures (in-memory SQLite)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde.workflow import models  # noqa: F401  registers workflow tables
from app.modules.aitde.mission import models as mission_models  # noqa: F401
from app.modules.aitde.scenario import models as scenario_models  # noqa: F401
from app.modules.aitde.contract import models as contract_models  # noqa: F401
from app.modules.aitde.execution import models as execution_models  # noqa: F401
from app.modules.aitde.data import models as data_models  # noqa: F401


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
def db_with_v34(db):
    """Alias of ``db`` for tests that exercise the full AITDE model set."""
    return db
