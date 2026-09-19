"""回填影响图边并输出模块关联覆盖率（Batch 260 / B3-2）。

用法（在 backend 目录下）：
    python scripts/backfill_impact_edges.py --project-id 1
    python scripts/backfill_impact_edges.py --project-id 1 --bundle-id 12
    python scripts/backfill_impact_edges.py --project-id 1 --dry-run

为什么需要它：B3-2 的 DoD 是「体育试点模块关联覆盖率 ≥90%」——这是个**度量**，
必须在真实数据上跑出来，不能靠单测里的合成数据代替（单测只证明算法与口径正确）。

输出 JSON（含逐发布包覆盖率与未覆盖模块清单），可直接作为工单/PR 证据。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models.release_bundle import ReleaseBundle  # noqa: E402
from app.services import impact_graph_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="回填影响图边并输出模块关联覆盖率")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--bundle-id", type=int, default=0, help="0 = 该项目下全部发布包")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写库")
    args = parser.parse_args()

    with SessionLocal() as db:
        try:
            if args.bundle_id:
                bundles = [db.get(ReleaseBundle, args.bundle_id)]
            else:
                bundles = list(
                    db.scalars(
                        select(ReleaseBundle)
                        .where(ReleaseBundle.project_id == args.project_id)
                        .order_by(ReleaseBundle.id.asc())
                    ).all()
                )
        except Exception as exc:
            # 刻意的宽捕获：本脚本的用途是给人看结论，要把"库没迁移"翻译成人话而不是抛堆栈。
            # 不要加抑制指令（质量棘轮里对应规则未启用，抑制本身会多出一条 RUF100）。
            print(
                json.dumps(
                    {
                        "error": "数据库不可用或尚未迁移",
                        "hint": "请先执行 `python -m alembic upgrade head`（或检查 DATABASE_URL）",
                        "detail": f"{type(exc).__name__}: {str(exc)[:200]}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
        bundles = [b for b in bundles if b is not None]
        if not bundles:
            print(json.dumps(
                {"project_id": args.project_id, "bundles": 0, "note": "该项目下没有发布包"},
                ensure_ascii=False,
                indent=2,
            ))
            return 1

        results = []
        for bundle in bundles:
            result = impact_graph_service.build_edges(
                db,
                project_id=args.project_id,
                bundle_id=bundle.id,
                dry_run=args.dry_run,
            )
            results.append(
                {
                    "bundle_id": bundle.id,
                    "version": result["version"],
                    "created": result["created"],
                    "updated": result["updated"],
                    "coverage": result["coverage"],
                }
            )

        totals = {
            "modules": sum(r["coverage"]["total_modules"] for r in results),
            "covered": sum(r["coverage"]["covered_modules"] for r in results),
        }
        overall = round(totals["covered"] / totals["modules"], 4) if totals["modules"] else 0.0
        print(json.dumps(
            {
                "project_id": args.project_id,
                "dry_run": args.dry_run,
                "bundles": len(results),
                "overall_coverage_rate": overall,
                "meets_90pct": overall >= 0.9,
                "per_bundle": results,
            },
            ensure_ascii=False,
            indent=2,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
