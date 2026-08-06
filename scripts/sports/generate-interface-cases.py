"""体育平台承接 — 接口用例生成（Batch 110：34 个生产真实样本字段级用例）。

从 evidence/batch-110/xhr-samples/xhr-samples-final.json 读取真实样本，
从 Test5 本地契约（test5-contracts/*.openapi.json）解析接口 schema（不依赖平台 API），
自动推导响应结构断言（envelope/data_keys/records 长度/首条记录核心字段），
调用平台 api_case_generation_service 生成字段级接口用例，直连生产库落库
（api_body/api_assertions/case_design_method/positive_negative/test_data_note）。

运行: <venv-python> scripts/sports/generate-interface-cases.py --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "test-platform-v2" / "backend"
CONTRACTS_DIR = REPO_ROOT / "test-platform-v2" / "tests" / "api-testing" / "specs" / "test5-contracts"
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "interface-cases"
SAMPLES_FILE = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "xhr-samples" / "xhr-samples-final.json"

MAX_CASES_PER_ENDPOINT = 40


def _load_generator():
    sys.path.insert(0, str(BACKEND_DIR))
    from app.services import api_case_generation_service as svc

    return svc


def _load_contracts() -> dict[str, dict]:
    """加载本地契约：path → {method: {summary, parameters, requestBody}}。"""
    out: dict[str, dict] = {}
    for f in CONTRACTS_DIR.glob("*.openapi.json"):
        if f.stat().st_size < 1024:
            continue
        try:
            spec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for path, ops in (spec.get("paths") or {}).items():
            for method, op in (ops or {}).items():
                if method not in ("get", "post", "put", "delete"):
                    continue
                out.setdefault(path, {})[method.upper()] = op
    return out


def _schema_for(contracts: dict, path: str, method: str) -> dict:
    op = contracts.get(path, {}).get(method)
    if not op:
        return {}
    schema: dict = {"body": {}, "query": [], "path": [], "header": []}
    for p in op.get("parameters") or []:
        ptype = (p.get("schema") or {}).get("type", "string")
        entry = {"name": p.get("name", ""), "required": bool(p.get("required")), "type": ptype}
        if p.get("in") == "query":
            schema["query"].append(entry)
        elif p.get("in") == "path":
            schema["path"].append(entry)
        elif p.get("in") == "header":
            schema["header"].append(entry)
    rb = op.get("requestBody") or {}
    content = rb.get("content") or {}
    js = content.get("application/json") or content.get("*/*") or {}
    body_schema = js.get("schema") or {}
    if isinstance(body_schema, dict):
        schema["body"] = {
            "properties": body_schema.get("properties") or {},
            "required": body_schema.get("required") or [],
        }
    return schema


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


def _fix_assertion_paths(assertions: list, response: str) -> list:
    """按样本真实响应形状修正响应结构断言路径（records/results/根列表）。"""
    if not response:
        return assertions
    try:
        body = json.loads(response)
    except Exception:
        return assertions
    data = body.get("data") if isinstance(body, dict) else None
    list_key = ""
    if isinstance(data, dict):
        for k in ("records", "results", "list", "items"):
            if isinstance(data.get(k), list):
                list_key = k
                break
    data_is_list = isinstance(data, list)
    out = []
    for a in assertions:
        if a.get("type") != "response_structure" or not a.get("path"):
            out.append(a)
            continue
        p = a["path"]
        if "records[" in p:
            if list_key and list_key != "records":
                p = p.replace("records[", f"{list_key}[")
            elif data_is_list:
                p = p.replace("data.records[0]", "data[0]")
        if p == "data.[]":
            p = "data"
        a = dict(a)
        a["path"] = p
        out.append(a)
    return out


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
            "response": s.get("response") or "",
        })
    return targets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    ap.add_argument("--templates", default="basic,boundary,invalid,security,idempotency,extreme,smoke,scenario,extra_param,security_ext,data_test")
    args = ap.parse_args()
    if not args.database_url:
        print("ERROR: 需要 --database-url / TP_DATABASE_URL", flush=True)
        return 1

    svc = _load_generator()
    templates = [t.strip() for t in args.templates.split(",") if t.strip()]
    targets = _load_targets()
    if not targets:
        print("ERROR: 无真实样本目标，先运行勘察/探测脚本", flush=True)
        return 1
    contracts = _load_contracts()

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
                method = t["real"]["method"]
                request_schema = _schema_for(contracts, t["path"], method)
                endpoint_data = {
                    "service_name": t["service"],
                    "module": t["module"],
                    "method": method,
                    "path": t["path"],
                    "summary": t["module"],
                    "request_schema": request_schema,
                }
                body_props = request_schema.get("body", {}).get("properties") or {}
                if body_props:
                    cases = svc.generate_cases_from_endpoint(
                        endpoint_data,
                        templates=templates,
                        real_samples=[t["real"]],
                    )
                else:
                    cases = svc.generate_cases_from_real_sample(endpoint_data, t["real"])
                cases = cases[:MAX_CASES_PER_ENDPOINT]
                print(f"[generate] {t['path']} cases={len(cases)} schema={'local' if body_props else 'real-sample'}", flush=True)

                # 清理该模块的旧批次用例（幂等重跑）
                cur.execute(
                    "DELETE FROM test_case WHERE project_id=1 AND case_type='api' AND module=%s "
                    "AND source='ai_generated' AND api_spec_ref=''",
                    (t["module"],),
                )

                imported = 0
                for c in cases:
                    # 补真实 query 参数（GET/POST 均适用，生成器未拼 query 时）
                    if t["real"].get("query"):
                        ep = c.get("api_endpoint") or t["path"]
                        if "?" not in ep:
                            qs = "&".join(f"{k}={v}" for k, v in t["real"]["query"].items())
                            c["api_endpoint"] = f"{ep}?{qs}"
                    if c.get("api_assertions"):
                        c["api_assertions"] = _fix_assertion_paths(c["api_assertions"], t.get("response") or "")
                    tags = list(c.get("tags") or [])
                    if "batch:110" not in tags:
                        tags.append("batch:110")
                        c["tags"] = tags
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
                    "schema_source": "local-contract" if body_props else "real-sample",
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
