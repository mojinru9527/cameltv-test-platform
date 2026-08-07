"""体育平台承接 — 功能用例 P0 标识（Batch 110，UI 自动化基线）。

P0 口径（Batch 110 QA 定义）：
  用户端关键用户路径（首页/赛事详情/直播间/资讯/搜索/登录注册/个人中心）→ 全部 P0；
  运营后台核心管理链路（账户/充值/提现/预测/内容/广告/装扮/消息/用户/系统核心模块）→ 模块命中 P0，其余回 P1；
  跨域生产新增模块（回放/世界杯）→ 命中 P0。

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

# 用户端关键域（全部 P0，Batch 111 用户确认补充：广告模块/联赛/球队/球员/回放）
P0_USER_DOMAINS = [
    "首页", "赛事详情", "直播间", "资讯", "搜索", "登录注册", "个人中心",
    "广告系统", "启动引导", "APP端数据与排行榜",
]

# 运营后台域（仅核心模块 P0，其余回 P1）
ADMIN_DOMAINS = [
    "财务管理", "赛事预测", "UGC管理", "商城管理", "广告管理", "装扮管理",
    "消息管理", "系统管理", "球队及联赛管理", "风控管理", "银钻任务管理", "用户管理",
]

# 运营后台整域 P0（核心治理链路，用户确认口径）
P0_ADMIN_DOMAINS = ["风控管理"]

ADMIN_P0_MODULES = [
    "%用户账户%", "%充值%", "%提现%", "%预测赛事%", "%用户参与%", "%奖励%",
    "%退回%", "%资讯%", "%热门搜索%", "%商品%", "%广告活动%", "%广告位%",
    "%头像框%", "%推送%", "%聊天室%", "%版本更新%", "%热门联赛%", "%热门球队%",
    "%屏蔽赛事视频%", "%风控%", "%银钻任务%", "%用户列表%", "%封禁%", "%举报%",
    "%意见反馈%", "%文章%", "%创作者%", "%购买记录%", "%勋章%",
    "%任务内容%", "%邀请好友%", "%任务完成记录%", "%聊天文案%", "%屏蔽%",
]

# 跨域生产新增模块（用户补充：联赛/球队/球员详情页 + 回放）
P0_MODULE_PATTERNS = [
    "%回放%", "%世界杯%", "%联赛详情%", "%球队详情%", "%球员详情%",
    "%球队榜%", "%球员榜%", "%联赛榜%", "%开屏广告%", "%跳过广告%",
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
    summary = {
        "p0_user_domains": P0_USER_DOMAINS,
        "admin_domains": ADMIN_DOMAINS,
        "p0_module_patterns": P0_MODULE_PATTERNS,
        "updated": {},
    }
    try:
        with conn.cursor() as cur:
            for dom in P0_USER_DOMAINS:
                cur.execute(
                    "UPDATE test_case SET priority='P0', updated_at=now() "
                    "WHERE project_id=1 AND is_deleted=false AND case_type='manual' "
                    "AND domain=%s AND priority<>'P0'",
                    (dom,),
                )
                summary["updated"][f"user:{dom}"] = cur.rowcount
            for dom in ADMIN_DOMAINS:
                cur.execute(
                    "UPDATE test_case SET priority='P1', updated_at=now() "
                    "WHERE project_id=1 AND is_deleted=false AND case_type='manual' "
                    "AND domain=%s AND priority='P0'",
                    (dom,),
                )
                summary["updated"][f"admin-reset:{dom}"] = cur.rowcount
            for dom in P0_ADMIN_DOMAINS:
                cur.execute(
                    "UPDATE test_case SET priority='P0', updated_at=now() "
                    "WHERE project_id=1 AND is_deleted=false AND case_type='manual' "
                    "AND domain=%s AND priority<>'P0'",
                    (dom,),
                )
                summary["updated"][f"admin-p0-domain:{dom}"] = cur.rowcount
            for pat in ADMIN_P0_MODULES:
                cur.execute(
                    "UPDATE test_case SET priority='P0', updated_at=now() "
                    "WHERE project_id=1 AND is_deleted=false AND case_type='manual' "
                    "AND module LIKE %s AND priority<>'P0'",
                    (pat,),
                )
                summary["updated"][f"admin-p0:{pat}"] = cur.rowcount
            for pat in P0_MODULE_PATTERNS:
                cur.execute(
                    "UPDATE test_case SET priority='P0', updated_at=now() "
                    "WHERE project_id=1 AND is_deleted=false AND case_type='manual' "
                    "AND module LIKE %s AND priority<>'P0'",
                    (pat,),
                )
                summary["updated"][f"pattern:{pat}"] = cur.rowcount
            cur.execute(
                "SELECT priority, COUNT(*) FROM test_case WHERE project_id=1 AND is_deleted=false "
                "AND case_type='manual' GROUP BY priority ORDER BY priority"
            )
            summary["priority_distribution"] = {str(r[0]): r[1] for r in cur.fetchall()}
            cur.execute(
                "SELECT module, COUNT(*) FROM test_case WHERE project_id=1 AND is_deleted=false "
                "AND case_type='manual' AND priority='P0' GROUP BY module ORDER BY module"
            )
            summary["p0_modules"] = {r[0]: r[1] for r in cur.fetchall()}
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "p0-cases-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] P0 分布: {summary['priority_distribution']}（P0 模块数 {len(summary['p0_modules'])}）")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
