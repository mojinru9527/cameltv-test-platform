"""体育平台承接 — 本地 AI 功能用例生成并同步生产库（Batch 102）。

背景: 生产 Railway 网关对同步 AI 请求有 ~300s 超时，大需求文档（92+ 功能点）的
AI 用例生成超过该限制（实测 300s 整 502）。本脚本复用平台同一套 ai_service
（DeepSeek key 本地可用）生成用例，再直连生产库写入 ai_raw + 审查队列，
随后用平台标准导入 API 落库，确保最终用例经由平台正式链路。

运行: <venv-python> scripts/sports/ai-generate-sync.py --password <pw> --database-url "$env:TP_DATABASE_URL"
凭据: --password / TP_ADMIN_PASSWORD（平台）；--database-url / TP_DATABASE_URL（Supabase，不回显）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "test-platform-v2" / "backend"
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-102"


def _load_ai_service():
    # 从 backend/.env 读取 AI 配置注入环境变量（settings 默认无 Key）
    env_files = [BACKEND_DIR / ".env", Path(r"F:/CamelTv/test-platform-v2/backend/.env")]
    for env_file in env_files:
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"')
            if key.startswith("AI_") and value and key not in os.environ:
                os.environ[key] = value
    sys.path.insert(0, str(BACKEND_DIR))
    from app.services import ai_service

    return ai_service


def _api_client(base: str, username: str, password: str) -> httpx.Client:
    c = httpx.Client(
        headers={"Origin": "https://swiftbugs.cn", "X-Project-Id": "1"},
        timeout=60,
    )
    r = c.post(base.rstrip("/") + "/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    tok = r.json()["data"]["access_token"]
    c.headers["Authorization"] = f"Bearer {tok}"
    return c


async def generate_one(
    ai_service,
    doc: dict,
    extraction: dict,
) -> dict:
    """本地运行平台同一套 AI 用例生成（use_extraction 语义）。"""
    result = await ai_service.generate_test_cases(
        content=doc.get("content") or "",
        file_type=doc.get("file_type") or "md",
        source_ref=doc.get("source_ref") or "",
        extraction=extraction,
    )
    return result


def sync_to_db(dsn: str, doc_id: int, ai_result: dict) -> None:
    """写入生产库 ai_raw + 审查队列（与平台 generate 端点副作用一致）。"""
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE requirement_document SET ai_raw=%s, status='generated', updated_at=now() "
                "WHERE id=%s AND project_id=1",
                (json.dumps(ai_result, ensure_ascii=False), doc_id),
            )
            if cur.rowcount != 1:
                print(f"[db] doc={doc_id} 未更新（rowcount={cur.rowcount}）", flush=True)
            cur.execute("DELETE FROM requirement_review WHERE requirement_id=%s", (doc_id,))
            cases = []
            idx = 0
            for c in ai_result.get("functional_cases", []):
                cases.append((idx, "func"))
                idx += 1
            for c in ai_result.get("api_cases", []):
                cases.append((idx, "api"))
                idx += 1
            for case_index, case_type in cases:
                cur.execute(
                    "INSERT INTO requirement_review (requirement_id, case_index, case_type, status, edited_data, "
                    "reviewer_id, reviewed_at) VALUES (%s,%s,%s,'pending','{}',0,NULL) "
                    "ON CONFLICT (requirement_id, case_type, case_index) DO NOTHING",
                    (doc_id, case_index, case_type),
                )
        conn.commit()
        print(f"[db] doc={doc_id} ai_raw+review 已同步（cases={len(cases)}）", flush=True)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://swiftbugs.cn/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    ap.add_argument("--doc-ids", default="1,3", help="逗号分隔的需求文档 ID（默认用户端/运营后台主文档）")
    args = ap.parse_args()
    if not args.password or not args.database_url:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD 与 --database-url / TP_DATABASE_URL", flush=True)
        return 1

    ai_service = _load_ai_service()
    base = args.backend_url.rstrip("/")
    client = _api_client(base, args.username, args.password)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"docs": []}

    for doc_id in [int(x) for x in args.doc_ids.split(",") if x.strip()]:
        doc = client.get(f"{base}/requirements/{doc_id}").json()["data"]
        ext = client.get(f"{base}/requirements/{doc_id}/extraction").json()["data"]
        modules = ext.get("modules") or []
        fp_count = sum(len(m.get("function_points") or []) for m in modules)
        print(f"[generate] doc={doc_id} {doc['title']} modules={len(modules)} fp={fp_count}（本地 AI）", flush=True)
        ai_result = await generate_one(ai_service, doc, {"modules": modules})
        func_count = len(ai_result.get("functional_cases") or [])
        api_count = len(ai_result.get("api_cases") or [])
        print(f"[generate] doc={doc_id} functional={func_count} api={api_count}", flush=True)

        out = EVIDENCE_DIR / f"local-ai-doc{doc_id}.json"
        out.write_text(json.dumps(ai_result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[evidence] saved: {out}", flush=True)

        sync_to_db(args.database_url, doc_id, ai_result)
        summary["docs"].append({
            "doc_id": doc_id,
            "title": doc["title"],
            "modules": len(modules),
            "fp": fp_count,
            "functional_cases": func_count,
            "api_cases": api_count,
            "evidence": str(out),
        })

    client.close()
    sum_file = EVIDENCE_DIR / "local-ai-generation-summary.json"
    sum_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] summary: {sum_file}", flush=True)
    print("[done] 本地 AI 生成完成并已同步生产库；下一步用平台 API 导入用例", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
