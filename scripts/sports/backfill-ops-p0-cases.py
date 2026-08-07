"""体育平台承接 — 补运营后台 P0 缺口用例（Batch 111，用户 P0 口径补充）。

缺口：用户管理（用户列表/封禁/屏蔽/举报/意见反馈）、球队及联赛管理-屏蔽赛事视频。
依据：运营后台生产菜单 nav.json（Batch 110 实测）。
运行: <venv-python> scripts/sports/backfill-ops-p0-cases.py --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-111"

CASES = [
    {"domain": "用户管理", "module": "用户列表", "title": "用户列表查询（分页/筛选）", "priority": "P0", "pn": "positive"},
    {"domain": "用户管理", "module": "用户封禁", "title": "用户封禁与解封", "priority": "P0", "pn": "positive"},
    {"domain": "用户管理", "module": "屏蔽记录", "title": "屏蔽记录查询", "priority": "P0", "pn": "positive"},
    {"domain": "用户管理", "module": "举报记录", "title": "举报记录查询与处理", "priority": "P0", "pn": "positive"},
    {"domain": "用户管理", "module": "意见反馈", "title": "意见反馈列表与处理", "priority": "P0", "pn": "positive"},
    {"domain": "球队及联赛管理", "module": "屏蔽赛事视频", "title": "屏蔽赛事视频配置", "priority": "P0", "pn": "positive"},
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
    inserted = 0
    try:
        with conn.cursor() as cur:
            for c in CASES:
                cur.execute(
                    "SELECT id FROM test_case WHERE project_id=1 AND is_deleted=false AND case_type='manual' "
                    "AND domain=%s AND title=%s",
                    (c["domain"], c["title"]),
                )
                if cur.fetchone():
                    continue
                steps = json.dumps([
                    {"step": 1, "action": f"运营后台进入「{c['module']}」页面（只读）", "expected": "页面正常渲染"},
                    {"step": 2, "action": "执行列表查询/记录处理（评审场景）", "expected": "结果正确"},
                ], ensure_ascii=False)
                cur.execute(
                    "INSERT INTO test_case (project_id, case_id, title, domain, module, is_deleted, case_type, "
                    "priority, status, tags, case_design_method, positive_negative, test_data_note, preconditions, "
                    "steps, expected_result, api_method, api_endpoint, api_headers, api_body, api_assertions, "
                    "api_spec_ref, last_response_json, last_run_status, source, source_req_id, source_doc_id, "
                    "source_case_index, review_status, review_comment, reviewer_id, created_at, updated_at) "
                    "VALUES (1,'',%s,%s,%s,false,'manual',%s,'active',%s,'场景法',%s,'运营后台生产菜单实测（Batch 110 nav.json）',"
                    "'运营后台只读账号',%s,%s,'','','[]','','[]','','','','ai_generated','',NULL,NULL,'draft','',0,now(),now())",
                    (
                        c["title"], c["domain"], c["module"], c["priority"],
                        json.dumps(["sports-platform", "admin", "P0"], ensure_ascii=False),
                        c["pn"], steps, "用例可执行且结果正确",
                    ),
                )
                inserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "ops-p0-cases-backfill.json").write_text(
        json.dumps({"inserted": inserted, "cases": CASES}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[db] 运营后台 P0 缺口用例插入 {inserted} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
