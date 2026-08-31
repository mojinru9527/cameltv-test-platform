"""V39-011 / §77-78 — reversible PostgreSQL migration drill.

The V3.9 Migration Gate (plan §78) does NOT require a full ``downgrade base``
(blocked by the historical ``create_all`` bootstrap); it requires the *last
release* to be reversible:

    PostgreSQL previous-head → current-head PASS
    current-head → previous-head  PASS

This drill is DB-agnostic: it runs against whatever ``DATABASE_URL`` points at
(SQLite for a fast local check, PostgreSQL in CI). It upgrades to the previous
head, upgrades to the current head, downgrades back to the previous head, then
upgrades to head again — and asserts the chain stays single-headed throughout.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _alembic(database_url: str, *args: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _current_and_previous_head() -> tuple[str, str | None]:
    from alembic.script import ScriptDirectory

    script = ScriptDirectory(str(BACKEND_ROOT / "alembic"))
    heads = script.get_heads()
    assert len(heads) == 1, f"expected single head, got {heads}"
    head = heads[0]
    revision = script.get_revision(head)
    return head, revision.down_revision


@pytest.fixture(scope="module")
def drill_db() -> str:
    """A DATABASE_URL to drill against (PostgreSQL in CI, temp SQLite locally)."""
    env_url = os.environ.get("DATABASE_URL")
    if env_url and env_url.startswith(("postgres", "postgresql")):
        yield env_url
        return
    # Local: throwaway SQLite.
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "drill.db"
        yield f"sqlite:///{db_path.as_posix()}"


@pytest.mark.slow
@pytest.mark.integration
def test_migration_drill_previous_head_is_reversible(drill_db: str) -> None:
    head_str, prev_str = _current_and_previous_head()
    assert prev_str, "current migration head must have a previous revision"

    # From a fresh DB: previous-head -> current-head -> previous-head -> current-head.
    rc, out = _alembic(drill_db, "upgrade", prev_str)
    assert rc == 0, f"upgrade previous-head failed:\n{out}"

    rc, out = _alembic(drill_db, "upgrade", "head")
    assert rc == 0, f"upgrade current-head failed:\n{out}"

    rc, out = _alembic(drill_db, "downgrade", prev_str)
    assert rc == 0, f"downgrade to previous-head failed:\n{out}"

    rc, out = _alembic(drill_db, "upgrade", "head")
    assert rc == 0, f"re-upgrade current-head failed:\n{out}"

    # The chain must stay single-headed after the round-trip.
    rc, out = _alembic(drill_db, "heads")
    assert rc == 0, f"alembic heads failed:\n{out}"
    heads = [line for line in out.splitlines() if "(head)" in line]
    assert len(heads) == 1, f"expected single head, got {heads}"
