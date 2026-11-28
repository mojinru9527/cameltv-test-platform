"""V16-024-R3 验收：本地 SQLite 备份/恢复演练可执行且校验完整。"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "ops" / "aiqe_backup_restore_drill.py"


def _load():
    spec = importlib.util.spec_from_file_location("aiqe_backup_restore_drill", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "app.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.execute("INSERT INTO alembic_version VALUES ('20261120_v16_014_catalog')")
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO demo VALUES (1, 'x')")
    conn.commit()
    conn.close()
    return path


def test_backup_restore_drill_passes_and_is_verifiable(tmp_path):
    db = _db(tmp_path)
    report = MODULE.run_drill(
        database_url=f"sqlite:///{db.as_posix()}",
        backup_dir=tmp_path / "backups",
        report_path=tmp_path / "report.json",
    )
    assert report["status"] == "PASS"
    assert report["integrity_check"] == "ok"
    assert report["alembic_revision"] == "20261120_v16_014_catalog"
    assert report["backup_sha256"] == report["restored_sha256"]
    assert "demo" in report["tables"] and "alembic_version" in report["tables"]
    assert report["scope"] == "LOCAL_SQLITE_ONLY"
    assert report["staging_postgres_drill"] == "NOT_RUN"
    saved = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert saved["status"] == "PASS"


def test_drill_rejects_non_sqlite_or_memory_or_missing(tmp_path):
    with pytest.raises(MODULE.DrillError):
        MODULE.run_drill(
            database_url="postgresql://u:p@localhost/db",
            backup_dir=tmp_path,
            report_path=tmp_path / "x.json",
        )
    with pytest.raises(MODULE.DrillError):
        MODULE.run_drill(
            database_url="sqlite:///:memory:",
            backup_dir=tmp_path,
            report_path=tmp_path / "x.json",
        )
    with pytest.raises(MODULE.DrillError):
        MODULE.run_drill(
            database_url=f"sqlite:///{(tmp_path / 'missing.db').as_posix()}",
            backup_dir=tmp_path,
            report_path=tmp_path / "x.json",
        )


def test_cli_exit_codes(tmp_path):
    db = _db(tmp_path)
    ok = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--database-url",
            f"sqlite:///{db.as_posix()}",
            "--backup-dir",
            str(tmp_path / "b"),
            "--report",
            str(tmp_path / "r.json"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert ok.returncode == 0, ok.stderr
    bad = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--database-url",
            "postgresql://x",
            "--backup-dir",
            str(tmp_path / "b"),
            "--report",
            str(tmp_path / "r2.json"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert bad.returncode != 0
    assert "staging" in bad.stderr.lower() or "postgres" in bad.stderr.lower()
