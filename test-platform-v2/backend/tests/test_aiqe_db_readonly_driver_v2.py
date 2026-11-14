"""v1.4 FIX-007：DB Read-only Driver 加固测试。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from app.aiqe.drivers.db_readonly_driver import (
    DbReadonlyDriver,
    QueryNotRegistered,
    QueryRegistry,
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


def test_dangerous_functions_rejected():
    for sql in (
        "SELECT pg_sleep(10)",
        "SELECT sleep(10)",
        "SELECT load_file('/etc/passwd')",
        "SELECT * FROM users FOR UPDATE",
    ):
        with pytest.raises(UnsafeSqlError):
            assert_readonly(sql)


def test_table_allowlist_blocks_cross_project(engine):
    driver = DbReadonlyDriver(engine, allowed_tables=["allowed_table"])
    with pytest.raises(UnsafeSqlError):
        driver.query("SELECT * FROM users")


def test_table_allowlist_allows_registered(engine):
    driver = DbReadonlyDriver(engine, allowed_tables=["users"])
    result = driver.query("SELECT id FROM users ORDER BY id")
    assert result.rows == [{"id": 1}, {"id": 2}]


def test_query_registry_only(engine):
    registry = QueryRegistry(
        {
            "users.by_id": {
                "sql": "SELECT name FROM users WHERE id = :id",
                "allowed_tables": ["users"],
                "max_rows": 1,
            }
        }
    )
    driver = DbReadonlyDriver(engine, registry=registry)
    result = driver.query(query_key="users.by_id", params={"id": 2})
    assert result.rows == [{"name": "bob"}]
    assert result.query_key == "users.by_id"
    with pytest.raises(QueryNotRegistered):
        driver.query(query_key="missing")


def test_field_length_truncated_and_marked(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE notes (body TEXT)")
        conn.exec_driver_sql("INSERT INTO notes (body) VALUES ('" + "x" * 50 + "')")
    driver = DbReadonlyDriver(engine, max_field_chars=10, allowed_tables=["notes"])
    result = driver.query("SELECT body FROM notes")
    assert result.rows[0]["body"].endswith("…[truncated]")
    assert result.truncated_fields == ["body"]


def test_row_limit_raises(engine):
    driver = DbReadonlyDriver(engine, max_rows=1, allowed_tables=["users"])
    with pytest.raises(RowLimitExceeded):
        driver.query("SELECT * FROM users")


def test_cte_alias_not_treated_as_table(engine):
    driver = DbReadonlyDriver(engine, allowed_tables=["users"])
    result = driver.query("WITH u AS (SELECT * FROM users) SELECT COUNT(*) AS n FROM u")
    assert result.rows == [{"n": 2}]


def test_audit_records_rejection(engine):
    driver = DbReadonlyDriver(engine, allowed_tables=["users"])
    with pytest.raises(UnsafeSqlError):
        driver.query("SELECT * FROM secret_table")
    assert driver.last_audit[-1].allowed is False
    assert "secret_table" in driver.last_audit[-1].reason
