"""体育平台承接 — 接口用例生产实跑与结果回填（Batch 110，C103-2/7）。

从生产库读取 Batch 110 生成的接口用例（api 类型、正向/冒烟/返回值结构），
以真实请求参数调用生产 API（api.cameltv.live），按 api_assertions 执行
响应结构断言，回填 last_response_json / last_run_status。

运行: <venv-python> scripts/sports/execute-interface-cases.py --database-url "$env:TP_DATABASE_URL"
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
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "interface-cases"
API_BASE = "https://api.cameltv.live"
MAX_RUNS = 120


def _assert_status(assertions: list, status: int) -> tuple[bool, str]:
    for a in assertions:
        if a.get("type") != "status_code":
            continue
        op = a.get("operator", "eq")
        exp = int(a.get("expected", 200))
        ok = {
            "eq": status == exp,
            "gte": status >= exp,
            "lte": status <= exp,
            "lt": status < exp,
            "gt": status > exp,
        }.get(op, False)
        if not ok:
            return False, f"status {status} 不满足 {op} {exp}"
    return True, ""


def _assert_structure(assertions: list, body: dict) -> tuple[bool, list[str]]:
    fails = []
    for a in assertions:
        if a.get("type") != "response_structure":
            continue
        path = a.get("path", "")
        kind = a.get("assert", "exists")
        if not path:
            continue
        parts = [p for p in path.split(".") if p and p != "[]"]
        node: object = body
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            elif isinstance(node, list) and p.isdigit() and int(p) < len(node):
                node = node[int(p)]
            else:
                node = None
                break
        if kind in ("exists", "not_empty", "is_object_or_array"):
            if node is None or (kind == "not_empty" and node in ("", [], {}, None)):
                fails.append(f"{path} {kind} 失败")
        elif kind == "len_lte":
            if isinstance(node, list) and len(node) > int(a.get("expected", 0)):
                fails.append(f"{path} 长度 {len(node)} > {a.get('expected')}")
    return len(fails) == 0, fails


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
    summary = {"runs": [], "passed": 0, "failed": 0, "errors": 0}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, api_method, api_endpoint, api_body, api_assertions "
                "FROM test_case WHERE project_id=1 AND is_deleted=false AND case_type='api' "
                "AND positive_negative IN ('positive','boundary') AND api_endpoint LIKE '%/camel-service/%' "
                "ORDER BY id LIMIT %s",
                (MAX_RUNS,),
            )
            rows = cur.fetchall()
        with httpx.Client(base_url=API_BASE, timeout=45, headers={"Accept": "application/json"}) as client:
            for row in rows:
                case_id, title, method, endpoint, api_body, api_assertions = row
                assertions = json.loads(api_assertions or "[]")
                url = endpoint
                body = None
                if method == "GET":
                    sep = "&" if "?" in url else "?"
                    url = f"{url}{sep}page=1&size=10" if "?" not in url else url
                else:
                    try:
                        body = json.loads(api_body or "{}")
                    except Exception:
                        body = {}
                started = time.time()
                try:
                    if method == "GET":
                        r = client.get(url)
                    else:
                        r = client.post(url, json=body)
                    elapsed = round(time.time() - started, 3)
                    resp_text = r.text[:250000]
                    try:
                        resp_json = r.json()
                    except Exception:
                        resp_json = {"_raw": resp_text[:500]}
                    status_ok, status_err = _assert_status(assertions, r.status_code)
                    struct_ok, struct_fails = _assert_structure(assertions, resp_json)
                    passed = status_ok and struct_ok
                    result = {
                        "status": r.status_code,
                        "elapsed_ms": int(elapsed * 1000),
                        "assertions_ok": passed,
                        "status_check": status_err or "ok",
                        "structure_fails": struct_fails,
                    }
                    with conn.cursor() as cur2:
                        cur2.execute(
                            "UPDATE test_case SET last_response_json=%s, last_run_status=%s, updated_at=now() WHERE id=%s",
                            (json.dumps(resp_json, ensure_ascii=False)[:200000], "passed" if passed else "failed", case_id),
                        )
                    summary["runs"].append({
                        "case_id": case_id, "title": title[:80], "method": method, "endpoint": endpoint,
                        "passed": passed, "result": result,
                    })
                    if passed:
                        summary["passed"] += 1
                    else:
                        summary["failed"] += 1
                    print(f"[run] {'PASS' if passed else 'FAIL'} {method} {endpoint} -> {r.status_code} {elapsed}s", flush=True)
                except Exception as exc:
                    summary["errors"] += 1
                    summary["runs"].append({"case_id": case_id, "endpoint": endpoint, "passed": False, "error": str(exc)[:200]})
                    print(f"[run] ERROR {endpoint}: {exc}", flush=True)
                with conn.cursor() as cur2:
                    pass
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "interface-execution-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] passed={summary['passed']} failed={summary['failed']} errors={summary['errors']}")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
