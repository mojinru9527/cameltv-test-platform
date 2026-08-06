"""体育平台承接 — 接口用例生成（Batch 110：34 个生产真实样本字段级用例）。

从 evidence/batch-110/xhr-samples/xhr-samples-final.json 读取真实样本，
自动推导响应结构断言（envelope/data_keys/records 长度/首条记录核心字段），
调用平台 api_case_generation_service 生成字段级接口用例，直连生产库落库
（api_body/api_assertions/case_design_method/positive_negative/test_data_note）。

运行: <venv-python> scripts/sports/generate-interface-cases.py --password <pw> --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx
import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "test-platform-v2" / "backend"
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "interface-cases"
SAMPLES_FILE = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "xhr-samples" / "xhr-samples-final.json"

MAX_CASES_PER_ENDPOINT = 40


def _load_generator():
    sys.path.insert(0, str(BACKEND_DIR))
    from app.services import api_case_generation_service as svc

    return svc


def _service_of(path: str) -> str:
    parts = path.lstrip("/").split("/")
    if parts and parts[0].endswith("-service"):
        return parts[0]
    return "camel-service"


def _parse_query(path: str) -> dict:
    if "?" not in path:
        return {}
    q = path.split("?", 1)[1]
    out = {}
    for pair in q.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k] = v
    return out


def _derive_response_meta(response: str) -> dict:
    """从真实响应推导响应结构断言元数据（Batch 107 返回值校验落地）。"""
    meta: dict = {}
    if not response or response.startswith("[too-large") or response.startswith("[body-unavailable"):
        return meta
    try:
        body = json.loads(response)
    except Exception:
        return meta
    if not isinstance(body, dict):
        return meta
    envelope = [k for k in body.keys() if isinstance(k, str)]
    if envelope:
        meta["response_envelope_keys"] = envelope[:8]
    data = body.get("data")
    if isinstance(data, dict):
        meta["data_keys"] = [k for k in data.keys() if isinstance(k, str)][:10]
        records = data.get("records") or data.get("results") or data.get("list") or data.get("items")
        if isinstance(records, list) and records:
            meta["record_count"] = min(len(records), 50)
            first = records[0]
            if isinstance(first, dict):
                meta["first_record_fields"] = [k for k in first.keys() if isinstance(k, str)][:8]
        elif isinstance(records, list):
            meta["record_count"] = 0
    elif isinstance(data, list) and data:
        meta["data_keys"] = ["[]"]
        if isinstance(data[0], dict):
            meta["first_record_fields"] = [k for k in data[0].keys() if isinstance(k, str)][:8]
    meta["assertion_design_hints"] = ["响应结构与真实调用一致", "业务状态码/核心字段非空", "列表长度不超过 size"]
    return meta


def _load_targets() -> list[dict]:
    if not SAMPLES_FILE.exists():
        print(f"[warn] 样本文件缺失 {SAMPLES_FILE}", flush=True)
        return []
    data = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))
    targets = []
    for s in data.get("samples", []):
        path = (s.get("path") or "").split("?")[0]
        if not path:
            continue
        method = (s.get("method") or "GET").upper()
        post_data = s.get("post_data") or ""
        body = {}
        if post_data:
            try:
                body = json.loads(post_data)
            except Exception:
                body = {"_raw": post_data}
        real = {
            "method": method,
            "url": s.get("url") or "https://api.cameltv.live" + path,
            "body": body,
            "query": _parse_query(s.get("path") or ""),
            "source": s.get("source") or s.get("module") or "生产真实样本（Batch 110 采集）",
        }
        real.update(_derive_response_meta(s.get("response") or ""))
        targets.append({
            "service": _service_of(path),
            "path": path,
            "module": s.get("module") or path,
            "real": real,
        })
    return targets


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
    ap.add_argument("--templates", default="basic,boundary,invalid,security,idempotency,extreme,smoke,scenario,extra_param,security_ext,data_test")
    args = ap.parse_args()
    if not args.password or not args.database_url:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD 与 --database-url / TP_DATABASE_URL", flush=True)
        return 1

    svc = _load_generator()
    base = args.backend_url.rstrip("/")
    client = _api_client(base, args.username, args.password)
    templates = [t.strip() for t in args.templates.split(",") if t.strip()]
    targets = _load_targets()
    if not targets:
        print("ERROR: 无真实样本目标，先运行勘察/探测脚本", flush=True)
        return 1

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
            for t in targets:
                r = client.get(
                    base + "/apitest/endpoints",
                    params={"keyword": t["path"], "page": 1, "page_size": 20},
                )
                r.raise_for_status()
                items = r.json()["data"].get("items", [])
                ep = next((e for e in items if e.get("path") == t["path"]), None)
                if not ep:
                    print(f"[skip] 未找到契约 {t['service']} {t['path']}（真实样本仍可生成）", flush=True)
                endpoint_data = {
                    "service_name": t["service"],
                    "module": t["module"],
                    "method": ep.get("method", t["real"]["method"]) if ep else t["real"]["method"],
                    "path": t["path"],
                    "summary": (ep.get("summary") or "") if ep else t["module"],
                    "request_schema": json.loads(ep.get("request_schema") or "{}") if ep else {},
                }
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
                cases = cases[:MAX_CASES_PER_ENDPOINT]
                print(f"[generate] {t['path']} cases={len(cases)}", flush=True)

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
                    "module": t["module"],
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
    print(f"[db] 接口用例导入 {total_imported} 条 / {len(summary['endpoints'])} 端点")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
