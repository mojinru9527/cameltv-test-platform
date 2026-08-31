"""V3.9-R2 DATA-001 — real DatabaseDriver execution primitives.

Verifies the driver actually runs parameterized SELECT / DML against a database
(not a recipe), enforces the statement-type allowlist + table allowlist + row cap,
and reports failures by credential-free category.
"""
from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine, text

from app.modules.aitde.drivers.database.base import DatabaseDriver, DatabaseQueryError


class SqliteTestDriver(DatabaseDriver):
    source_type = "SQLITE"

    def build_url(self) -> str:
        return f"sqlite:///{self.config['db_path']}"


@pytest.fixture()
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE user (id INTEGER PRIMARY KEY, status TEXT, name TEXT)"))
        conn.execute(text("INSERT INTO user (id, status, name) VALUES (1, 'ACTIVE', 'alice')"))
        conn.execute(text("INSERT INTO user (id, status, name) VALUES (2, 'EXPIRED', 'bob')"))
    engine.dispose()
    yield path
    os.remove(path)


def _driver(db_path, allowlist=None):
    return SqliteTestDriver({"db_path": db_path, "table_allowlist": allowlist}, "ref")


def test_execute_select_returns_real_rows(db_path):
    driver = _driver(db_path, allowlist=["user"])
    rows = driver.execute_select("SELECT id, status, name FROM user WHERE status = :s", {"s": "ACTIVE"})
    assert len(rows) == 1
    assert rows[0]["name"] == "alice"


def test_execute_select_respects_row_limit(db_path):
    driver = _driver(db_path, allowlist=["user"])
    rows = driver.execute_select("SELECT * FROM user", {}, row_limit=1)
    assert len(rows) == 1


def test_execute_select_rejects_non_select(db_path):
    driver = _driver(db_path, allowlist=["user"])
    with pytest.raises(DatabaseQueryError) as exc_info:
        driver.execute_select("DELETE FROM user WHERE id = 1", {})
    assert exc_info.value.code == "ONLY_SELECT"


def test_execute_select_rejects_unallowlisted_table(db_path):
    driver = _driver(db_path, allowlist=["other"])
    with pytest.raises(DatabaseQueryError) as exc_info:
        driver.execute_select("SELECT * FROM user", {}, table="user")
    assert exc_info.value.code == "TABLE_NOT_ALLOWLISTED"


def test_execute_dml_runs_inside_transaction(db_path):
    driver = _driver(db_path, allowlist=["user"])
    result = driver.execute_dml("INSERT INTO user (id, status, name) VALUES (:id, :status, :name)", {"id": 3, "status": "NORMAL", "name": "carol"})
    assert result["rowcount"] == 1
    rows = driver.execute_select("SELECT name FROM user WHERE id = :id", {"id": 3})
    assert rows[0]["name"] == "carol"


def test_execute_dml_rejects_select(db_path):
    driver = _driver(db_path, allowlist=["user"])
    with pytest.raises(DatabaseQueryError) as exc_info:
        driver.execute_dml("SELECT * FROM user", {})
    assert exc_info.value.code == "ONLY_WRITE"
