"""Independently verify the Batch-273 migration applies and reverses on a clean DB.

Creates a scratch SQLite DB, runs alembic upgrade head, asserts BOTH DDL changes
from the new revision really exist, then downgrade -1 and asserts they are gone,
then upgrade head again for idempotency. Scratch DB is deleted at the end.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(sys.argv[1]).resolve()
py = sys.executable


def run_alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": url}
    return subprocess.run(
        [py, "-m", "alembic", *args],
        cwd=BACKEND, env=env, capture_output=True, text=True,
    )


def schema(db: str) -> tuple[bool, bool, bool]:
    con = sqlite3.connect(db)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(ai_jobs)")}
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        indexes = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        # P1-6 热路径：配额查询按 (project_id, created_at) 过滤，必须有复合索引，
        # 否则每次 LLM 调用都要在该项目的历史行上扫描。
        composite = any(
            "model_usage_ledger" in n and "project" in n and "created" in n
            for n in indexes
        ) or bool(
            con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='index' AND tbl_name='model_usage_ledger' "
                "AND sql LIKE '%project_id%' AND sql LIKE '%created_at%'"
            ).fetchone()
        )
        return ("attempt_count" in cols, "knowledge_trigger_debounce" in tables, composite)
    finally:
        con.close()


failures = 0


def expect(label: str, got, want) -> None:
    global failures
    ok = got == want
    if not ok:
        failures += 1
    print(f"{'OK  ' if ok else 'FAIL'} {label}: got={got} want={want}")


with tempfile.TemporaryDirectory() as td:
    db = str(Path(td) / "mig_probe.db")
    url = f"sqlite:///{db}"

    up = run_alembic(url, "upgrade", "head")
    print("== alembic upgrade head ==")
    if up.returncode != 0:
        print(up.stdout[-2000:])
        print(up.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    attempt, debounce, composite = schema(db)
    expect("after upgrade: ai_jobs.attempt_count exists", attempt, True)
    expect("after upgrade: knowledge_trigger_debounce exists", debounce, True)
    expect("after upgrade: composite (project_id, created_at) index exists", composite, True)

    print("\n== alembic downgrade -1 ==")
    down = run_alembic(url, "downgrade", "-1")
    if down.returncode != 0:
        print(down.stdout[-2000:])
        print(down.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    attempt, debounce, composite = schema(db)
    expect("after downgrade: attempt_count gone", attempt, False)
    expect("after downgrade: debounce table gone", debounce, False)
    expect("after downgrade: composite index gone", composite, False)

    print("\n== alembic upgrade head again (idempotency) ==")
    again = run_alembic(url, "upgrade", "head")
    expect("re-upgrade exit code", again.returncode, 0)
    attempt, debounce, composite = schema(db)
    expect("after re-upgrade: attempt_count exists", attempt, True)
    expect("after re-upgrade: debounce table exists", debounce, True)
    expect("after re-upgrade: composite index exists", composite, True)

    heads = run_alembic(url, "heads")
    head_lines = [ln for ln in heads.stdout.splitlines() if "(head)" in ln]
    expect("single head", len(head_lines), 1)
    if head_lines:
        rev = head_lines[0].split()[0]
        print(f"     head={rev} (len={len(rev)})")
        expect("revision id <= 128 chars (PG varchar(128))", len(rev) <= 128, True)

print()
if failures:
    print(f"{failures} CHECK(S) FAILED")
    sys.exit(1)
print("MIGRATION VERIFICATION PASSED")
