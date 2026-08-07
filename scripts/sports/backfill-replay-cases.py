"""体育平台承接 — 补回放模块功能用例（Batch 111，用户 P0 口径补充）。

生产页面 /match-replay + /match-replay/{id}，接口 replay/list + replay/get（Batch 110 实测）。
用例域：回放（用户端），P0。
运行: <venv-python> scripts/sports/backfill-replay-cases.py --database-url "$env:TP_DATABASE_URL"
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
    {
        "title": "回放列表加载（赛事回放页面）",
        "module": "回放列表",
        "priority": "P0",
        "positive_negative": "positive",
        "steps": [
            {"step": 1, "action": "打开生产页面 /match-replay", "expected": "回放列表渲染"},
            {"step": 2, "action": "校验接口 replay/list 返回记录", "expected": "记录非空且含标题/封面/比赛时间"},
        ],
        "expected_result": "回放列表正常加载，接口响应结构正确",
        "note": "生产实测：replay/list total=29，id=107123464706493798",
    },
    {
        "title": "回放列表分页边界",
        "module": "回放列表",
        "priority": "P0",
        "positive_negative": "boundary",
        "steps": [
            {"step": 1, "action": "请求 replay/list page=999999 size=10", "expected": "返回空 records 或 4xx，不 5xx"},
        ],
        "expected_result": "超出总页数时分页边界正确",
        "note": "生产实测接口 replay/list",
    },
    {
        "title": "回放详情页加载",
        "module": "回放详情",
        "priority": "P0",
        "positive_negative": "positive",
        "steps": [
            {"step": 1, "action": "打开生产页面 /match-replay/107123464706493798", "expected": "回放详情渲染（标题/封面/视频区）"},
            {"step": 2, "action": "校验接口 replay/get", "expected": "返回 2xx 且结构正确"},
        ],
        "expected_result": "回放详情页正常加载",
        "note": "生产实测：replay/get 200",
    },
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
                    "AND domain='回放' AND title=%s",
                    (c["title"],),
                )
                if cur.fetchone():
                    continue
                cur.execute(
                    "INSERT INTO test_case (project_id, case_id, title, domain, module, is_deleted, case_type, "
                    "priority, status, tags, case_design_method, positive_negative, test_data_note, preconditions, "
                    "steps, expected_result, api_method, api_endpoint, api_headers, api_body, api_assertions, "
                    "api_spec_ref, last_response_json, last_run_status, source, source_req_id, source_doc_id, "
                    "source_case_index, review_status, review_comment, reviewer_id, created_at, updated_at) "
                    "VALUES (1,'',%s,'回放',%s,false,'manual',%s,'active',%s,'场景法',%s,%s,'生产只读勘察',"
                    "%s,%s,'','','[]','','[]','','','','ai_generated','',NULL,NULL,'draft','',0,now(),now())",
                    (
                        c["title"], c["module"], c["priority"],
                        json.dumps(["sports-platform", "replay", "P0"], ensure_ascii=False),
                        c["positive_negative"], c["note"],
                        json.dumps(c["steps"], ensure_ascii=False), c["expected_result"],
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
    (EVIDENCE_DIR / "replay-cases-backfill.json").write_text(
        json.dumps({"inserted": inserted, "cases": CASES}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[db] 回放用例插入 {inserted} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
