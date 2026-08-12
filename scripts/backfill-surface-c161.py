#!/usr/bin/env python
"""Batch 162 / C161-3 — 回填 test_cases.surface 列（对齐 classify_case_surface 计算值）。

用法（生产/本地）:
    DATABASE_URL="postgresql://..." python scripts/backfill-surface-c161.py [--dry-run]

仅更新 surface 与规则计算值不一致的行；默认 dry-run 打印统计。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "test-platform-v2" / "backend"
sys.path.insert(0, str(BACKEND))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    ap.add_argument("--dry-run", action="store_true", help="只统计不落库")
    args = ap.parse_args()

    if not args.database_url:
        print("ERROR: 需要 DATABASE_URL 环境变量或 --database-url")
        return 1

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.models.test_case import TestCase
    from app.services.test_case_taxonomy import classify_case_surface

    engine = create_engine(args.database_url)
    updated = 0
    skipped = 0
    with Session(engine) as db:
        rows = db.scalars(select(TestCase)).all()
        for r in rows:
            computed = classify_case_surface(r.domain or "", r.case_type or "manual", r.module or "")
            if computed == "其他":
                skipped += 1
                continue
            if r.surface != computed:
                print(f"  update id={r.id} surface {r.surface!r} -> {computed!r} | {r.domain}/{r.module}")
                if not args.dry_run:
                    r.surface = computed
                updated += 1
        if not args.dry_run and updated:
            db.commit()
    print(f"done: updated={updated} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
