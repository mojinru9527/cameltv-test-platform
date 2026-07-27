"""Batch 19 test data cleanup script.

Deletes all test data created during acceptance verification for batch-19.
Run after QA verification passes to restore the database to its pre-verification state.

Usage:
    python scripts/cleanup_batch19_test_data.py [--dry-run]
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Resolve database path relative to backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "cameltv.db"

# Tag/marker used to identify batch-19 test data
BATCH19_MARKER = "batch19_verification"


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def count_table(conn: sqlite3.Connection, table: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return -1


def cleanup(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """Delete batch-19 test data. Returns counts of deleted rows per table."""
    deleted = {}

    # 1. Delete test cases created during verification
    #    - Filter by title containing batch19 marker or tags field
    #    - Also delete any cases with 'batch19' in tags
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM test_cases WHERE tags LIKE ? OR title LIKE ?",
        (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
    ).fetchone()
    case_count = result["cnt"]
    if not dry_run and case_count > 0:
        conn.execute(
            "DELETE FROM test_cases WHERE tags LIKE ? OR title LIKE ?",
            (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
        )
    deleted["test_cases"] = case_count

    # 2. Delete API endpoints/assets created during verification
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM api_endpoints WHERE tags LIKE ? OR summary LIKE ?",
        (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
    ).fetchone()
    ep_count = result["cnt"]
    if not dry_run and ep_count > 0:
        conn.execute(
            "DELETE FROM api_endpoints WHERE tags LIKE ? OR summary LIKE ?",
            (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
        )
    deleted["api_endpoints"] = ep_count

    # 3. Delete API services created during verification
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM api_services WHERE tags LIKE ? OR display_name LIKE ?",
        (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
    ).fetchone()
    svc_count = result["cnt"]
    if not dry_run and svc_count > 0:
        conn.execute(
            "DELETE FROM api_services WHERE tags LIKE ? OR display_name LIKE ?",
            (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
        )
    deleted["api_services"] = svc_count

    # 4. Delete requirements created during verification
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM requirements WHERE title LIKE ? OR source_ref LIKE ?",
        (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
    ).fetchone()
    req_count = result["cnt"]
    if not dry_run and req_count > 0:
        conn.execute(
            "DELETE FROM requirements WHERE title LIKE ? OR source_ref LIKE ?",
            (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
        )
    deleted["requirements"] = req_count

    # 5. Delete test plans created during verification
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM test_plans WHERE name LIKE ?",
        (f"%{BATCH19_MARKER}%",),
    ).fetchone()
    plan_count = result["cnt"]
    if not dry_run and plan_count > 0:
        conn.execute(
            "DELETE FROM test_plans WHERE name LIKE ?",
            (f"%{BATCH19_MARKER}%",),
        )
    deleted["test_plans"] = plan_count

    # 6. Delete execution results created during verification
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM test_executions WHERE name LIKE ? OR tags LIKE ?",
        (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
    ).fetchone()
    exec_count = result["cnt"]
    if not dry_run and exec_count > 0:
        conn.execute(
            "DELETE FROM test_executions WHERE name LIKE ? OR tags LIKE ?",
            (f"%{BATCH19_MARKER}%", f"%{BATCH19_MARKER}%"),
        )
    deleted["test_executions"] = exec_count

    # 7. Delete defects created during verification
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM defects WHERE title LIKE ?",
        (f"%{BATCH19_MARKER}%",),
    ).fetchone()
    defect_count = result["cnt"]
    if not dry_run and defect_count > 0:
        conn.execute(
            "DELETE FROM defects WHERE title LIKE ?",
            (f"%{BATCH19_MARKER}%",),
        )
    deleted["defects"] = defect_count

    if not dry_run:
        conn.commit()

    return deleted


def main():
    parser = argparse.ArgumentParser(description="Clean up batch-19 verification test data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    args = parser.parse_args()

    conn = get_connection()
    try:
        # Record pre-cleanup counts
        print("=" * 60)
        print("Batch 19 Test Data Cleanup")
        print("=" * 60)
        print(f"Database: {DB_PATH}")
        print(f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'LIVE (will delete)'}")
        print()

        # Show current table counts
        tables = ["test_cases", "api_endpoints", "api_services", "requirements", "test_plans", "test_executions", "defects"]
        print("Current table counts:")
        for t in tables:
            cnt = count_table(conn, t)
            status = f"{cnt}" if cnt >= 0 else "N/A"
            print(f"  {t}: {status}")
        print()

        # Perform cleanup
        deleted = cleanup(conn, dry_run=args.dry_run)

        total = sum(deleted.values())
        print("Rows to be deleted:" if args.dry_run else "Rows deleted:")
        for table, count in deleted.items():
            if count > 0:
                print(f"  {table}: {count}")
        print(f"  TOTAL: {total}")

        if args.dry_run:
            print()
            print("DRY RUN complete. Run without --dry-run to actually delete.")
        else:
            print()
            print("Cleanup complete. Database restored to pre-verification state.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
