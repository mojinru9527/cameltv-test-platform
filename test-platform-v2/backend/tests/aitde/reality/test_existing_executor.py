"""V3.9-R2 DATA-002 — ExistingExecutor real SELECT + NOT_FOUND.

Verifies the EXISTING strategy really queries the DataSource (never a recipe),
returns the physical rows it found, and FAILS (NOT_FOUND) when no row matches
instead of declaring success.
"""
from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine, text

from app.modules.aitde.data.executors.existing_executor import ExistingExecutor
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
        conn.execute(
            text("CREATE TABLE membership (id INTEGER PRIMARY KEY, status TEXT, user_id INTEGER)")
        )
        conn.execute(text("INSERT INTO membership (id, status, user_id) VALUES (1, 'ACTIVE', 5)"))
    engine.dispose()
    driver = _SqliteDriver({"db_path": path, "table_allowlist": ["membership"]}, "ref")
    yield driver
    os.remove(path)


def test_execute_find_returns_real_rows(db_driver):
    result = ExistingExecutor.execute_find(
        db_driver, "membership", {"status": "ACTIVE", "user_id": 5}
    )
    assert result["found"] is True
    assert result["physical_rows"][0]["status"] == "ACTIVE"
    assert result["physical_rows"][0]["user_id"] == 5


def test_execute_find_respects_row_limit(db_driver):
    driver = _SqliteDriver(
        {"db_path": db_driver.config["db_path"], "table_allowlist": ["membership"]}, "ref"
    )
    result = ExistingExecutor.execute_find(driver, "membership", {"status": "ACTIVE"}, row_limit=1)
    assert len(result["physical_rows"]) == 1


def test_execute_find_no_match_is_not_found(db_driver):
    with pytest.raises(DatabaseQueryError) as exc:
        ExistingExecutor.execute_find(db_driver, "membership", {"status": "EXPIRED"})
    assert exc.value.code == "NOT_FOUND"


def test_execute_find_rejects_unallowlisted_table(db_driver):
    with pytest.raises(DatabaseQueryError) as exc:
        ExistingExecutor.execute_find(db_driver, "user", {"status": "ACTIVE"})
    assert exc.value.code == "TABLE_NOT_ALLOWLISTED"


def test_execute_find_rejects_unsafe_identifier(db_driver):
    with pytest.raises(DatabaseQueryError) as exc:
        ExistingExecutor.execute_find(db_driver, "membership; DROP TABLE", {"status": "ACTIVE"})
    assert exc.value.code == "UNSAFE_TABLE"


def test_execute_find_rejects_empty_where(db_driver):
    with pytest.raises(DatabaseQueryError) as exc:
        ExistingExecutor.execute_find(db_driver, "membership", {})
    assert exc.value.code == "EMPTY_WHERE"
