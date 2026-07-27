# -*- coding: utf-8 -*-
"""
Batch 27 M5.1 -- Knowledge center legacy data domain migration (one-shot)

Rules:
  1. source_type = 'platform_doc'          -> knowledge_domain = 'platform'
  2. source_type = 'capture'               -> knowledge_domain = 'platform'
  3. source_ref contains work-logs path    -> knowledge_domain = 'platform'
  4. source_ref contains lanhuapp.com      -> knowledge_domain = 'project'
  5. source_type = 'lanhu_evidence'        -> knowledge_domain = 'project'
  6. source_type IN (test_case, openapi, api_catalog, api_test,
     execution, ui_test_execution, production_test, requirement)
                                           -> knowledge_domain = 'project'

Safety:
  - Export full CSV snapshot to backups/ before migration
  - Spot-check 20 records per category
  - Show dry-run change summary, confirm before executing

Usage:
  python scripts/migrate_knowledge_domain.py          # interactive (shows dry-run then confirms)
  python scripts/migrate_knowledge_domain.py --yes     # non-interactive (CI/automation)
  python scripts/migrate_knowledge_domain.py --dry-run # preview only, no changes
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

# Force UTF-8 stdout on Windows to avoid GBK encoding errors
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ── Database discovery ──

def _find_db() -> str:
    candidates = [
        "data/platform.db",
        "cameltv.db",
        "app.db",
        "test_platform.db",
    ]
    backend_dir = Path(__file__).resolve().parent.parent  # scripts/ -> backend/
    for rel in candidates:
        p = backend_dir / rel
        if p.exists():
            import sqlite3
            try:
                c = sqlite3.connect(str(p))
                c.execute("SELECT 1 FROM knowledge_source LIMIT 1")
                c.close()
                return str(p)
            except Exception:
                continue
    raise FileNotFoundError(
        "Cannot find database with knowledge_source table. "
        f"Searched: {[str(backend_dir / c) for c in candidates]}"
    )


# ── Classification engine ──

def classify_domain(
    source_type: str,
    source_ref: str,
    title: str = "",
    metadata_json: str = "",
) -> str:
    """Return 'project' or 'platform'. Empty string = cannot determine (keep current)."""

    ref_lower = source_ref.lower() if source_ref else ""

    # —— Platform development knowledge ——
    if source_type == "platform_doc":
        return "platform"
    if source_type == "capture":
        return "platform"
    if "work-logs" in ref_lower or "work_logs" in ref_lower:
        return "platform"
    if "agent team" in ref_lower or "agent team" in title.lower():
        return "platform"
    if metadata_json and '"knowledge_domain"' in metadata_json:
        import json
        try:
            md = json.loads(metadata_json)
            if isinstance(md, dict) and md.get("knowledge_domain") == "platform":
                return "platform"
        except (json.JSONDecodeError, TypeError):
            pass

    # —— Project knowledge ——
    if source_type == "lanhu_evidence":
        return "project"
    if "lanhuapp.com" in ref_lower:
        return "project"
    if source_type in (
        "test_case", "openapi", "api_catalog", "api_test",
        "execution", "ui_test_execution", "production_test",
        "requirement",
    ):
        return "project"

    # Cannot determine -> keep current value
    return ""


# ── CSV snapshot ──

def export_snapshot(db_path: str, backup_dir: str) -> str:
    import sqlite3
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(backup_dir, f"knowledge_source_snapshot_{ts}.csv")
    os.makedirs(backup_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM knowledge_source ORDER BY id")
    col_names = [d[0] for d in cur.description]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(col_names)
        w.writerows(cur.fetchall())

    conn.close()
    print(f"  [SNAPSHOT] CSV saved: {out_path}")
    return out_path


# ── Change detection ──

def compute_changes(db_path: str) -> list[dict]:
    """Scan all rows, return list of records needing migration."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, source_type, title, source_ref, knowledge_domain, metadata_json "
        "FROM knowledge_source ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()

    changes: list[dict] = []
    for r in rows:
        old = r["knowledge_domain"] or "project"
        new = classify_domain(
            r["source_type"] or "",
            r["source_ref"] or "",
            r["title"] or "",
            r["metadata_json"] or "",
        )
        if new and new != old:
            changes.append({
                "id": r["id"],
                "source_type": r["source_type"],
                "title": (r["title"] or "")[:60],
                "old_domain": old,
                "new_domain": new,
                "reason": _reason(r["source_type"], r["source_ref"]),
            })
    return changes


def _reason(source_type: str, source_ref: str) -> str:
    if source_type == "platform_doc":
        return "source_type=platform_doc -> platform"
    if source_type == "capture":
        return "source_type=capture -> platform"
    if source_ref and "work-logs" in source_ref.lower():
        return "source_ref contains work-logs -> platform"
    if source_ref and "lanhuapp.com" in source_ref.lower():
        return "source_ref contains lanhuapp.com -> project"
    if source_type == "lanhu_evidence":
        return "source_type=lanhu_evidence -> project"
    if source_type in (
        "test_case", "openapi", "api_catalog", "api_test",
        "execution", "ui_test_execution", "production_test", "requirement",
    ):
        return f"source_type={source_type} -> project"
    return "unknown rule"


# ── Apply migration ──

def apply_changes(db_path: str, changes: list[dict]) -> int:
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    updated = 0
    for ch in changes:
        cur.execute(
            "UPDATE knowledge_source SET knowledge_domain = ? WHERE id = ?",
            (ch["new_domain"], ch["id"]),
        )
        updated += 1
    conn.commit()
    conn.close()
    return updated


# ── Spot check ──

def spot_check(db_path: str, sample_size: int = 20) -> None:
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for domain, label in [("project", "Project Knowledge"), ("platform", "Platform Dev")]:
        cur.execute(
            "SELECT id, title, source_type, knowledge_domain, source_ref "
            "FROM knowledge_source WHERE knowledge_domain = ? "
            "ORDER BY RANDOM() LIMIT ?",
            (domain, sample_size),
        )
        rows = cur.fetchall()
        print(f"\n  [SPOT-CHECK] {label} (knowledge_domain={domain}) sampled {len(rows)}:")
        mismatches = 0
        for r in rows:
            expected = classify_domain(
                r["source_type"] or "",
                r["source_ref"] or "",
                r["title"] or "",
            )
            actual = r["knowledge_domain"]
            ok = (not expected) or (expected == actual)
            if not ok:
                mismatches += 1
                print(f"     MISMATCH [{r['id']}] expected={expected} actual={actual} "
                      f"type={r['source_type']} title={r['title'][:50]}")
        if mismatches == 0:
            print(f"     OK: all {len(rows)} records consistent")
        else:
            print(f"     WARNING: {mismatches}/{len(rows)} mismatched")

    conn.close()


# ── Summary ──

def print_summary(db_path: str) -> None:
    import sqlite3
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM knowledge_source")
    total = cur.fetchone()[0]

    cur.execute(
        "SELECT knowledge_domain, COUNT(*) FROM knowledge_source "
        "GROUP BY knowledge_domain ORDER BY COUNT(*) DESC"
    )
    print("\n  [SUMMARY] knowledge_domain distribution after migration:")
    for domain, cnt in cur.fetchall():
        pct = cnt / total * 100 if total else 0
        label = "Platform Dev" if domain == "platform" else (
            "Project Knowledge" if domain == "project" else domain
        )
        print(f"     {domain} ({label}): {cnt} ({pct:.1f}%)")

    conn.close()


# ── Main ──

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch 27 M5.1 - Knowledge center domain migration"
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation, execute directly")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only, no modifications")
    parser.add_argument("--spot-check-size", type=int, default=20, help="Sample size per category")
    args = parser.parse_args(argv)

    db_path = _find_db()
    backup_dir = os.path.join(os.path.dirname(db_path), "..", "backups")
    backup_dir = os.path.abspath(backup_dir)

    print(f"[DB] {db_path}")
    print(f"[SNAPSHOT DIR] {backup_dir}")

    # 1. Scan for changes
    changes = compute_changes(db_path)

    if not changes:
        print("\n[OK] No migration needed - all records match classification rules")
        spot_check(db_path, args.spot_check_size)
        print_summary(db_path)
        return 0

    # 2. Preview
    print(f"\n[DETECTED] {len(changes)} records need migration:\n")
    print(f"   {'ID':<6} {'Type':<20} {'Title':<50} {'Old->New'}")
    print(f"   {'-'*6} {'-'*20} {'-'*50} {'-'*12}")
    for ch in changes:
        print(f"   {ch['id']:<6} {ch['source_type']:<20} {ch['title']:<50} "
              f"{ch['old_domain']}->{ch['new_domain']}")

    if args.dry_run:
        print(f"\n[DRY-RUN] Above changes would be applied. Add --yes to execute.")
        return 0

    # 3. Confirm
    if not args.yes:
        resp = input(
            f"\n[CONFIRM] Apply migration to {len(changes)} records? [y/N] "
        ).strip().lower()
        if resp not in ("y", "yes"):
            print("Cancelled.")
            return 1

    # 4. Snapshot -> Execute -> Spot-check -> Summary
    export_snapshot(db_path, backup_dir)
    updated = apply_changes(db_path, changes)
    print(f"\n  [APPLIED] Updated {updated} records")
    spot_check(db_path, args.spot_check_size)
    print_summary(db_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
