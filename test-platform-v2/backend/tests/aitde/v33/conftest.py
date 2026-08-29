"""Shared AITDE V3.3 unit-test fixtures (in-memory SQLite)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
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
