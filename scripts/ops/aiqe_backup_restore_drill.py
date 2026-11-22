"""V16-024-R3：AIQE 本地备份/恢复演练（SQLite，可重复执行）。

用途：
- 在无 staging/生产同构集群时，先证明备份→恢复→完整性/版本校验链路可执行；
- 生产 PostgreSQL 演练仍需在 staging 用同构数据执行（本脚本对非 SQLite URL fail closed）。

用法：
  python scripts/ops/aiqe_backup_restore_drill.py \
    --database-url sqlite:///./data/app.db \
    --backup-dir ./work-logs/evidence/aiqe-v16/backup-drill \
    --report ./work-logs/evidence/aiqe-v16/backup-drill/report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


class DrillError(RuntimeError):
    pass


def _sqlite_path(database_url: str) -> Path:
    url = str(database_url or "").strip()
    if not url.startswith("sqlite:"):
        raise DrillError("本地演练仅支持 sqlite: URL；PostgreSQL 请在 staging 执行同构演练")
    raw = url.removeprefix("sqlite:///").removeprefix("sqlite://").removeprefix("sqlite:")
    if not raw or raw.startswith(":memory:"):
        raise DrillError("拒绝内存数据库：演练需要可恢复的持久化文件")
    path = Path(raw)
    if not path.exists():
        raise DrillError(f"数据库文件不存在: {path}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA integrity_check").fetchone()
    return str(row[0] if row else "unknown")


def _revision(conn: sqlite3.Connection) -> str:
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return str(row[0]) if row else ""
    except sqlite3.OperationalError:
        return ""


def _tables(conn: sqlite3.Connection) -> list[str]:
    return sorted(
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    )


def run_drill(*, database_url: str, backup_dir: str | Path, report_path: str | Path) -> dict:
    source = _sqlite_path(database_url)
    backup_root = Path(backup_dir)
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_file = backup_root / f"aiqe-{stamp}.db"
    restore_file = backup_root / f"aiqe-{stamp}-restored.db"

    started = time.monotonic()
    source_conn = sqlite3.connect(source)
    try:
        source_conn.execute("PRAGMA wal_checkpoint(FULL)")
        with sqlite3.connect(backup_file) as backup_conn:
            source_conn.backup(backup_conn)
        source_revision = _revision(source_conn)
        source_integrity = _integrity(source_conn)
    finally:
        source_conn.close()
    if source_integrity != "ok":
        raise DrillError(f"源库 integrity_check 失败: {source_integrity}")

    # 恢复演练：把备份复制到新文件并用 SQLite 打开校验（不覆盖源库）。
    restore_file.write_bytes(backup_file.read_bytes())
    with sqlite3.connect(restore_file) as restored:
        restored_integrity = _integrity(restored)
        restored_revision = _revision(restored)
        restored_tables = _tables(restored)
    if restored_integrity != "ok":
        raise DrillError(f"恢复库 integrity_check 失败: {restored_integrity}")
    if source_revision and source_revision != restored_revision:
        raise DrillError(
            f"恢复后 alembic revision 不一致: {source_revision} != {restored_revision}"
        )
    backup_sha = _sha256(backup_file)
    restored_sha = _sha256(restore_file)
    if backup_sha != restored_sha:
        raise DrillError("恢复文件 SHA256 与备份不一致")
    elapsed = time.monotonic() - started
    report = {
        "schema_version": "1.0",
        "status": "PASS",
        "executed_at": datetime.now(UTC).isoformat(),
        "database_url": str(database_url),
        "source": str(source),
        "backup_file": str(backup_file),
        "restore_file": str(restore_file),
        "backup_sha256": backup_sha,
        "restored_sha256": restored_sha,
        "alembic_revision": restored_revision,
        "table_count": len(restored_tables),
        "tables": restored_tables,
        "integrity_check": restored_integrity,
        "duration_seconds": round(elapsed, 3),
        "scope": "LOCAL_SQLITE_ONLY",
        "staging_postgres_drill": "NOT_RUN",
    }
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--backup-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    try:
        report = run_drill(
            database_url=args.database_url,
            backup_dir=args.backup_dir,
            report_path=args.report,
        )
    except (DrillError, OSError, sqlite3.Error) as exc:
        print(f"::error::backup_restore_drill: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report["status"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
