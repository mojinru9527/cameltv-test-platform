"""体育平台承接 — 接口用例生成（Batch 103：真实业务参数基线）。

对功能需求驱动的关键接口：取平台契约 request_schema + 生产/测试真实请求样本，
调用平台 api_case_generation_service（全模板）生成接口用例，直连生产库落库
（含 api_body/api_assertions/case_design_method/positive_negative/test_data_note）。

运行: <venv-python> scripts/sports/generate-interface-cases.py --password <pw> --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "test-platform-v2" / "backend"
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-103"

# 目标接口 + 真实样本（生产/测试环境回填或按功能需求捕获）
TARGETS = [
    {
        "service": "camel-service",
        "path": "/ee/news/list_visible",
        "real": {
            "method": "POST",
            "url": "https://api.cameltv.live/camel-service/ee/news/list_visible",
            "body": {
                "sorts": [{"key": "top", "sort": "desc"}, {"key": "updateTime", "sort": "desc"}],
                "page": 2,
                "size": 30,
                "queryList": [{"isOrNotRange": 0, "key": "language", "type": "String", "value1": "0", "value2": ""}],
                "locale": "en",
            },
            "source": "用户提供真实请求样本（新闻列表翻页+语言过滤）",
        },
    },
    {
        "service": "account-service",
        "path": "/ee/ads/activity/get",
        "real": {
            "method": "POST",
            "url": "https://api.cameltv.live/account-service/ee/ads/activity/get",
            "body": {"displayPlatform": "PC", "displayPage": "INDEX"},
            "source": "生产首页真实 XHR 样本（2026-08-06 Playwright 抓取）",
        },
    },
    {
        "service": "account-service",
        "path": "/ee/client/general",
        "real": {
            "method": "GET",
            "url": "https://api.cameltv.live/account-service/ee/client/general",
            "query": {},
            "source": "生产首页真实 XHR 样本（2026-08-06 Playwright 抓取）",
        },
    },
]


def _load_generator():
    sys.path.insert(0, str(BACKEND_DIR))
    from app.services import api_case_generation_service as svc

    return svc


def _api_client(base: str, username: str, password: str) -> httpx.Client:
    c = httpx.Client(
        headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"},
        timeout=60,
    )
    r = c.post(base.rstrip("/") + "/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    ap.add_argument("--templates", default="basic,boundary,invalid,security,idempotency,extreme")
    args = ap.parse_args()
    if not args.password or not args.database_url:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD 与 --database-url / TP_DATABASE_URL", flush=True)
        return 1

    svc = _load_generator()
    base = args.backend_url.rstrip("/")
    client = _api_client(base, args.username, args.password)
    templates = [t.strip() for t in args.templates.split(",") if t.strip()]

    dsn = args.database_url
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"endpoints": []}
    total_imported = 0

    try:
        with conn.cursor() as cur:
            for t in TARGETS:
                # 1) 平台契约取 endpoint schema
                r = client.get(
                    base + "/apitest/endpoints",
                    params={"keyword": t["path"], "page": 1, "page_size": 20},
                )
                r.raise_for_status()
                items = r.json()["data"].get("items", [])
                ep = next((e for e in items if e.get("path") == t["path"]), None)
                if not ep:
                    print(f"[skip] 未找到契约 {t['service']} {t['path']}", flush=True)
                    continue
                endpoint_data = {
                    "service_name": t["service"],
                    "module": ep.get("module", ""),
                    "method": ep.get("method", "GET"),
                    "path": ep.get("path", ""),
                    "summary": ep.get("summary", ""),
                    "request_schema": json.loads(ep.get("request_schema") or "{}"),
                }

                # 2) 真实样本基线生成：schema 有字段用规则生成器；否则用真实样本字段级生成
                schema = endpoint_data["request_schema"]
                body_props = (schema.get("body") or {}).get("properties") or {}
                if body_props:
                    cases = svc.generate_cases_from_endpoint(
                        endpoint_data,
                        templates=templates,
                        real_samples=[t["real"]],
                    )
                else:
                    cases = svc.generate_cases_from_real_sample(endpoint_data, t["real"])
                print(f"[generate] {t['path']} cases={len(cases)}", flush=True)

                # 3) 直连生产库落库（新字段列已由 Batch 103 迁移）
                imported = 0
                for c in cases:
                    steps = json.dumps(c.get("steps", []), ensure_ascii=False)
                    headers = json.dumps(c.get("api_headers", {}), ensure_ascii=False)
                    assertions = json.dumps(c.get("api_assertions", []), ensure_ascii=False)
                    body = c.get("api_body", "")
                    cur.execute(
                        "INSERT INTO test_case (project_id, case_id, title, domain, module, is_deleted, "
                        "case_type, priority, status, tags, case_design_method, positive_negative, test_data_note, "
                        "preconditions, steps, expected_result, api_method, api_endpoint, api_headers, api_body, "
                        "api_assertions, api_spec_ref, last_response_json, last_run_status, source, source_req_id, source_doc_id, "
                        "source_case_index, review_status, review_comment, reviewer_id, created_at, updated_at) "
                        "VALUES (1,'',%s,'接口测试',%s,false,'api',%s,'active',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'','','',"
                        "'ai_generated','',NULL,NULL,'draft','',0,now(),now())",
                        (
                            c.get("title", ""),
                            c.get("module", ""),
                            c.get("priority", "P2"),
                            json.dumps(c.get("tags", []), ensure_ascii=False),
                            c.get("case_design_method", ""),
                            c.get("positive_negative", ""),
                            c.get("test_data_note", ""),
                            c.get("preconditions", ""),
                            steps,
                            c.get("expected_result", ""),
                            c.get("api_method", ""),
                            c.get("api_endpoint", ""),
                            headers,
                            body,
                            assertions,
                        ),
                    )
                    imported += 1
                total_imported += imported
                summary["endpoints"].append({
                    "service": t["service"],
                    "path": t["path"],
                    "real_source": t["real"]["source"],
                    "generated": len(cases),
                    "imported": imported,
                })
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    out = EVIDENCE_DIR / "interface-cases-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[db] 接口用例导入 {total_imported} 条", flush=True)
    print(f"[evidence] {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
