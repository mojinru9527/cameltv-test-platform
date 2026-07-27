"""Check for schema drift between Alembic migrations and SQLAlchemy ORM models.

Detects tables/columns that exist in ORM models but have no corresponding Alembic
migration. This prevents the common "works in dev (AUTO_CREATE_TABLES=true) but
breaks in production (Alembic-only)" failure mode.

Usage:
  python scripts/check_migration_drift.py

Environment:
  DATABASE_URL — PostgreSQL connection string (required; SQLite not supported for
                 introspection comparison).

Exit code: 0 = no drift, 1 = drift detected (blocking), 2 = setup error.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Ensure the backend package root is on sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────

def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("::error::DATABASE_URL is required for drift check (PostgreSQL only)")
        sys.exit(2)
    if "sqlite" in url.lower():
        print("::error::SQLite is not supported for drift check. Use PostgreSQL.")
        sys.exit(2)
    return url


def _get_schema_tables(engine: Engine) -> dict[str, set[str]]:
    """Return {table_name: {column_names}} for all user tables.

    Excludes the alembic_version metadata table.
    """
    insp = inspect(engine)
    tables: dict[str, set[str]] = {}
    for tname in sorted(insp.get_table_names()):
        if tname == "alembic_version":
            continue
        cols = {col["name"] for col in insp.get_columns(tname)}
        tables[tname] = cols
    return tables


def _drop_all_user_tables(engine: Engine) -> None:
    """Drop every user table (CASCADE) so the DB is clean for the next step."""
    insp = inspect(engine)
    table_names = [t for t in insp.get_table_names() if t != "alembic_version"]
    if not table_names:
        return
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS " + ", ".join(
            f'"{t}"' for t in table_names
        ) + " CASCADE"))
        conn.commit()


def _run_alembic_upgrade() -> bool:
    """Run `alembic upgrade head` in the backend directory. Returns True on success."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        env={**os.environ},  # inherit DATABASE_URL
    )
    if result.returncode != 0:
        print("::error::alembic upgrade head failed:")
        print(result.stderr)
        return False
    return True


# ── main ─────────────────────────────────────────────────────────────

def main() -> int:
    db_url = _db_url()
    print(f"🔍 Checking schema drift on PostgreSQL…")

    # 1 ── Run Alembic migrations on a fresh DB ───────────────────────
    engine = create_engine(db_url)
    _drop_all_user_tables(engine)

    if not _run_alembic_upgrade():
        return 2

    alembic_schema = _get_schema_tables(engine)
    print(f"   Alembic head → {len(alembic_schema)} tables")

    # 2 ── Run ORM create_all on a clean DB ────────────────────────────
    _drop_all_user_tables(engine)

    from app.core.db import Base  # noqa: E402
    import app.models  # noqa: F401 — ensure all models registered

    Base.metadata.create_all(engine)

    orm_schema = _get_schema_tables(engine)
    print(f"   ORM create_all → {len(orm_schema)} tables")

    # 3 ── Compare ─────────────────────────────────────────────────────
    has_drift = False

    orm_tables = set(orm_schema.keys())
    alembic_tables = set(alembic_schema.keys())

    # Tables in ORM but missing from alembic (most critical)
    missing_tables = sorted(orm_tables - alembic_tables)
    if missing_tables:
        has_drift = True
        for t in missing_tables:
            cols = ", ".join(sorted(orm_schema[t])) if t in orm_schema else ""
            print(f"::warning file=app/models/__init__.py::Table '{t}' ({cols}) exists in ORM models but has no Alembic migration — missing 'alembic revision --autogenerate'?")

    # Tables in alembic but missing from ORM (stale migration)
    extra_tables = sorted(alembic_tables - orm_tables)
    for t in extra_tables:
        print(f"::warning file=alembic/versions/::Table '{t}' exists in Alembic but not in ORM models — stale migration?")

    # Column-level drift
    for tname in sorted(orm_tables & alembic_tables):
        orm_cols = orm_schema[tname]
        alembic_cols = alembic_schema[tname]
        missing_cols = sorted(orm_cols - alembic_cols)
        extra_cols = sorted(alembic_cols - orm_cols)
        if missing_cols:
            has_drift = True
            for c in missing_cols:
                print(f"::warning file=app/models/__init__.py::Table '{tname}': column '{c}' exists in ORM model but missing from Alembic migration")
        if extra_cols:
            for c in extra_cols:
                print(f"::warning file=alembic/versions/::Table '{tname}': column '{c}' in Alembic but not in ORM model — stale?")

    # 4 ── Summary ─────────────────────────────────────────────────────
    if not has_drift:
        print("✅ No schema drift — Alembic migrations match ORM models")
        return 0
    else:
        print("\n❌ Schema drift detected! Run the following locally:")
        print("   alembic revision --autogenerate -m 'fix_schema_drift'")
        print("   alembic upgrade head")
        return 1


if __name__ == "__main__":
    sys.exit(main())
