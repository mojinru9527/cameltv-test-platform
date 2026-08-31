"""CERT-005 — Production read-only DBA write-denial certification.

Connects to a real read-only DBA account and verifies the security invariant the
V3.9 plan §74 requires: SELECT is allowed, while INSERT / UPDATE / DELETE / DDL
(ALTER) and a CTE with a write are ALL denied by the database role — so a
``READONLY`` production data source can never mutate production data even if a
buggy driver attempts a write.

Gated on ``CERT5_PG_URL`` (a read-only account, e.g.
``postgresql://p_ro:ro_pw@127.0.0.1:5433/cert5_db``); skipped when unset so the
suite stays green on hosts without a RO account. Run in CI / the certification
job with the variable set.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

_URL = os.environ.get("CERT5_PG_URL")


@pytest.fixture()
def ro_engine():
    if not _URL:
        pytest.skip("CERT5_PG_URL not set (RO PG account required)")
    eng = create_engine(_URL)
    yield eng
    eng.dispose()


def _attempt(engine: object, sql: str) -> str:
    """Run a statement; return 'ok' if it executed, else the denial reason."""
    with engine.connect() as conn:
        try:
            conn.execute(text(sql))
            return "ok"
        except Exception as exc:  # noqa: BLE001 — assert the denial category
            return str(exc).splitlines()[0]


def test_prod_ro_select_is_allowed(ro_engine):
    with ro_engine.connect() as conn:
        rows = conn.execute(text("SELECT count(*) AS c FROM membership")).all()
        assert int(rows[0][0]) >= 0


def test_prod_ro_insert_denied(ro_engine):
    assert "denied" in _attempt(ro_engine, "INSERT INTO membership (status, user_id) VALUES ('N', 1)") or "permission" in _attempt(ro_engine, "INSERT INTO membership (status, user_id) VALUES ('N', 1)")


def test_prod_ro_update_denied(ro_engine):
    assert "denied" in _attempt(ro_engine, "UPDATE membership SET status='X' WHERE id=1") or "permission" in _attempt(ro_engine, "UPDATE membership SET status='X' WHERE id=1")


def test_prod_ro_delete_denied(ro_engine):
    assert "denied" in _attempt(ro_engine, "DELETE FROM membership WHERE id=1") or "permission" in _attempt(ro_engine, "DELETE FROM membership WHERE id=1")


def test_prod_ro_ddl_denied(ro_engine):
    assert "denied" in _attempt(ro_engine, "ALTER TABLE membership ADD COLUMN xx int") or "permission" in _attempt(ro_engine, "ALTER TABLE membership ADD COLUMN xx int") or "owner" in _attempt(ro_engine, "ALTER TABLE membership ADD COLUMN xx int")


def test_prod_ro_cte_write_denied(ro_engine):
    sql = "WITH ins AS (INSERT INTO membership (status, user_id) VALUES ('X', 1) RETURNING id) SELECT count(*) FROM ins"
    assert "denied" in _attempt(ro_engine, sql) or "permission" in _attempt(ro_engine, sql)
