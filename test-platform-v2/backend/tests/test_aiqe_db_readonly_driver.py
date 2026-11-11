"""M2 / TA-014：DB Read-only Driver 单测（SQLite）。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from app.aiqe.drivers.db_readonly_driver import (
    DbReadonlyDriver,
    RowLimitExceeded,
    UnsafeSqlError,
    assert_readonly,
)


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://")
    with eng.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.exec_driver_sql("INSERT INTO users (id, name) VALUES (1, 'alice'), (2, 'bob')")
    return eng


def test_select_returns_rows_and_columns(engine):
    result = DbReadonlyDriver(engine).query("SELECT id, name FROM users ORDER BY id")
    assert result.columns == ["id", "name"]
    assert result.rows == [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]
    assert result.row_count == 2


def test_params_binding(engine):
    result = DbReadonlyDriver(engine).query(
        "SELECT name FROM users WHERE id = :id", {"id": 2}
    )
    assert result.rows == [{"name": "bob"}]


def test_keyword_inside_literal_allowed(engine):
    result = DbReadonlyDriver(engine).query("SELECT 'please update' AS note")
    assert result.rows == [{"note": "please update"}]


def test_comments_allowed(engine):
    result = DbReadonlyDriver(engine).query("-- update later\nSELECT COUNT(*) AS n FROM users")
    assert result.rows == [{"n": 2}]


def test_cte_select_allowed(engine):
    result = DbReadonlyDriver(engine).query(
        "WITH u AS (SELECT * FROM users) SELECT name FROM u WHERE id = 1"
    )
    assert result.rows == [{"name": "alice"}]


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO users (id, name) VALUES (3, 'x')",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN age INTEGER",
        "CREATE TABLE t (id INTEGER)",
        "TRUNCATE TABLE users",
        "PRAGMA table_info(users)",
        "SELECT 1; DROP TABLE users",
    ],
)
def test_write_and_multi_statement_rejected(engine, sql):
    driver = DbReadonlyDriver(engine)
    with pytest.raises(UnsafeSqlError):
        driver.query(sql)


def test_row_limit_exceeded(engine):
    driver = DbReadonlyDriver(engine, max_rows=1)
    with pytest.raises(RowLimitExceeded):
        driver.query("SELECT * FROM users")


def test_assert_readonly_direct():
    assert assert_readonly("SELECT 1").startswith("SELECT")
    with pytest.raises(UnsafeSqlError):
        assert_readonly("")
    with pytest.raises(UnsafeSqlError):
        assert_readonly("SELECT 1; SELECT 2")
