"""体育平台承接 — 接口用例平台批量执行 + 回填验证（Batch 111，C110-3）。

依赖：C110-3 回填改造合入并部署生产后执行。
流程：登录 → 取 batch:110 接口用例 id → POST /apitest/tasks（生产环境 + confirm_prod）
      → 轮询任务 → 核对 TestCase.last_response_json/last_run_status 回填 → 证据 JSON。

运行: <venv-python> scripts/sports/run-batch-execution.py --password <pw> --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import httpx
import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-111"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    args = ap.parse_args()
    if not args.password or not args.database_url:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD 与 --database-url / TP_DATABASE_URL", flush=True)
        return 1

    dsn = args.database_url
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM test_case WHERE project_id=1 AND is_deleted=false AND case_type='api' "
            "AND tags::text LIKE '%%batch:110%%' ORDER BY id"
        )
        case_ids = [r[0] for r in cur.fetchall()]
        cur.execute(
            "SELECT COUNT(*) FILTER (WHERE last_run_status='passed'), COUNT(*) FILTER (WHERE last_run_status='failed'), COUNT(*) "
            "FROM test_case WHERE project_id=1 AND is_deleted=false AND case_type='api' AND tags::text LIKE '%%batch:110%%'"
        )
        before = {"passed": cur.fetchone()[0]}
    conn.close()
    print(f"[cases] batch:110 api 用例 {len(case_ids)} 条；执行前 passed={before['passed']}", flush=True)

    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=120,
                      headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"

        env_data = c.get("/environments").json().get("data", {})
        items = env_data.get("items", env_data) if isinstance(env_data, dict) else env_data
        env = next((e for e in items if "生产" in str(e.get("name", ""))), None)
        if not env:
            print("ERROR: 未找到生产环境", flush=True)
            return 1
        env_id = env["id"]
        print(f"[env] {env.get('name')} id={env_id}", flush=True)

        r = c.post("/apitest/tasks", json={
            "name": "体育平台-批量执行-Batch111",
            "case_ids": case_ids,
            "environment_id": env_id,
            "confirm_prod": True,
        })
        r.raise_for_status()
        task = r.json()["data"]
        task_id = task["id"]
        print(f"[task] created id={task_id} status={task['status']} total={task['total']}", flush=True)

        for _ in range(120):
            time.sleep(10)
            t = c.get(f"/apitest/tasks/{task_id}").json()["data"]
            if t["status"] in ("success", "failed", "cancelled"):
                print(f"[task] done status={t['status']} passed={t.get('passed')} failed={t.get('failed')} skipped={t.get('skipped')}", flush=True)
                break

    # 回填核对
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_run_status, COUNT(*) FROM test_case WHERE project_id=1 AND is_deleted=false "
            "AND case_type='api' AND tags::text LIKE '%%batch:110%%' GROUP BY last_run_status"
        )
        backfill = {str(r[0]): r[1] for r in cur.fetchall()}
        cur.execute(
            "SELECT COUNT(*) FROM test_case WHERE project_id=1 AND is_deleted=false AND case_type='api' "
            "AND tags::text LIKE '%%batch:110%%' AND last_response_json IS NOT NULL AND last_response_json <> ''"
        )
        backfill["has_response"] = cur.fetchone()[0]
    conn.close()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "batch-execution-summary.json"
    out.write_text(json.dumps({
        "task_id": task_id, "env_id": env_id, "case_count": len(case_ids),
        "backfill": backfill, "before": before,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
