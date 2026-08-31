"""V3.9-R2 DATA-002 — DbFixtureExecutor real INSERT + SELECT VERIFY."""
from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine, text

from app.modules.aitde.data.executors.db_executor import DbFixtureExecutor
from app.modules.aitde.drivers.database.base import DatabaseDriver, DatabaseQueryError


class _SqliteDriver(DatabaseDriver):
    source_type = "SQLITE"

    def build_url(self) -> str:
        return f"sqlite:///{self.config['db_path']}"


@pytest.fixture()
def db_driver():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE membership (id INTEGER PRIMARY KEY, status TEXT, user_id INTEGER)"))
    engine.dispose()
    driver = _SqliteDriver({"db_path": path, "table_allowlist": ["membership"]}, "ref")
    yield driver
    os.remove(path)


def test_execute_create_inserts_and_verifies(db_driver):
    result = DbFixtureExecutor.execute_create(
        db_driver, "membership", {"status": "ACTIVE", "user_id": 5}
    )
    assert result["created"] is True
    assert result["physical_row"]["status"] == "ACTIVE"
    assert result["physical_row"]["user_id"] == 5


def test_execute_create_rejects_unallowlisted_table(db_driver):
    with pytest.raises(DatabaseQueryError) as exc:
        DbFixtureExecutor.execute_create(db_driver, "user", {"status": "ACTIVE"})
    assert exc.value.code == "TABLE_NOT_ALLOWLISTED"


def test_execute_create_rejects_unsafe_identifier(db_driver):
    with pytest.raises(DatabaseQueryError) as exc:
        DbFixtureExecutor.execute_create(db_driver, "membership; DROP TABLE", {"status": "ACTIVE"})
    assert exc.value.code == "UNSAFE_TABLE"
