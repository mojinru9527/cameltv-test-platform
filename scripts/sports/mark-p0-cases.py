"""体育平台承接 — 功能用例 P0 标识（Batch 110，UI 自动化基线）。

按「P0 功能用例 → UI 自动化映射」清单，将核心功能模块的功能用例优先级更新为 P0。
仅更新 is_deleted=false 的 manual 功能用例（不覆盖接口用例的既有优先级语义）。

运行: <venv-python> scripts/sports/mark-p0-cases.py --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110"

# P0 模块（用户端关键用户路径 + 运营后台核心管理链路）
P0_MODULES = [
    "首页", "赛事详情", "直播间", "资讯", "搜索", "我的", "回放", "世界杯",
    "联赛", "球队", "登录注册", "用户账户", "财务管理", "赛事预测",
    "UGC管理", "内容管理", "商城管理", "广告管理", "装扮管理", "消息", "用户管理", "系统管理",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    args = ap.parse_args()
    if not args.database_url:
        print("ERROR: 需要 --database-url / TP_DATABASE_URL", flush=True)
        return 1
    dsn = args.database_url
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    summary = {"p0_modules": P0_MODULES, "updated_by_module": {}}
    try:
        with conn.cursor() as cur:
            for mod in P0_MODULES:
                cur.execute(
                    "UPDATE test_case SET priority='P0', updated_at=now() "
                    "WHERE project_id=1 AND is_deleted=false AND case_type='manual' "
                    "AND module=%s AND priority<>'P0'",
                    (mod,),
                )
                updated = cur.rowcount
                summary["updated_by_module"][mod] = updated
                print(f"[P0] {mod}: {updated} 条已标记 P0", flush=True)
            cur.execute(
                "SELECT priority, COUNT(*) FROM test_case WHERE project_id=1 AND is_deleted=false "
                "AND case_type='manual' AND domain IN ('体育平台-用户端','体育平台-运营后台') "
                "GROUP BY priority ORDER BY priority"
            )
            summary["priority_distribution"] = {str(r[0]): r[1] for r in cur.fetchall()}
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "p0-cases-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(summary["updated_by_module"].values())
    print(f"[done] P0 标记 {total} 条，分布: {summary['priority_distribution']}")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
