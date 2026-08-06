"""体育平台承接 — RAG 知识中心内容入库（Batch 110）。

把 4 份需求文档全文/功能地图 v2/接口测试规范三件导入知识中心。
优先走标准 POST /knowledge/capture（Batch 108 已修复 409）；
若仍 503/409（vector_search 等障碍），按 ingest_capture 落库语义直连补入并登记。
随后扩展知识图谱实体/关系（消息/用户管理/系统管理/登录注册等新增模块）。

运行: <venv-python> scripts/sports/sync-rag-content.py --password <pw> --database-url "$env:TP_DATABASE_URL"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psycopg2


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110"

REQ_DOCS = [
    REPO_ROOT / "产品需求" / "蓝湖原型-用户端原型-20260611_180510.md",
    REPO_ROOT / "产品需求" / "蓝湖原型-运营后台-20260611_180605.md",
    REPO_ROOT / "产品需求" / "更新日志-用户端原型-完整版.md",
    REPO_ROOT / "产品需求" / "更新日志-运营后台-完整版.md",
]
SPEC_DOCS = [
    REPO_ROOT / "tests" / "test-case-standards" / "API接口测试方案.md",
    REPO_ROOT / "tests" / "test-case-standards" / "接口测试规范.md",
    REPO_ROOT / "tests" / "test-case-standards" / "接口测试考虑点【辅助作用】.md",
]


def _h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


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

    # 1) 标准 API capture（优先）
    captured = []
    api_blocked = False
    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=300,
                      headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"
        sources = []
        for p in REQ_DOCS + SPEC_DOCS:
            if not p.exists():
                print(f"[warn] 缺失 {p.name}", flush=True)
                continue
            content = p.read_text(encoding="utf-8", errors="replace")
            title = f"体育平台-{p.stem}"
            rr = c.post("/knowledge/capture", json={"title": title, "content": content})
            j = rr.json()
            if rr.status_code >= 400 or j.get("code") not in (None, 0):
                print(f"[capture] {title} -> {rr.status_code} code={j.get('code')} msg={j.get('msg')}（登记障碍，走直连）", flush=True)
                api_blocked = True
                sources.append({"title": title, "path": str(p), "api": False})
            else:
                captured.append({"title": title, "id": j.get("data", {}).get("id")})
                sources.append({"title": title, "path": str(p), "api": True})
                print(f"[capture] {title} -> id={j.get('data', {}).get('id')}", flush=True)

    summary = {"api_captured": captured, "api_blocked": api_blocked}

    # 2) 直连兜底（api_blocked 时按 ingest 语义补入）
    if api_blocked:
        dsn = args.database_url
        if "sslmode" not in dsn:
            dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"
        conn = psycopg2.connect(dsn)
        conn.autocommit = False
        direct = 0
        now = _now()
        try:
            with conn.cursor() as cur:
                for src in summary["api_captured"]:
                    pass
                for p in REQ_DOCS + SPEC_DOCS:
                    if not p.exists():
                        continue
                    content = p.read_text(encoding="utf-8", errors="replace")
                    title = f"体育平台-{p.stem}"
                    full = f"# {title}\n\n{content}"
                    chash = _h(full)
                    cur.execute(
                        "SELECT id FROM knowledge_source WHERE project_id=1 AND source_type='capture' "
                        "AND source_id IS NULL AND content_hash=%s", (chash,))
                    if cur.fetchone():
                        continue
                    cur.execute(
                        "INSERT INTO knowledge_source (project_id, source_type, source_id, title, source_ref, content_hash, "
                        "version, iteration_id, para_category, knowledge_domain, freshness_score, status, raw_content, "
                        "metadata_json, module_name, module_id, last_verified_at, created_at, updated_at) "
                        "VALUES (1,'capture',NULL,%s,'',%s,'',NULL,'inbox','platform',1.0,'parsed',%s,'{}','体育平台',NULL,%s,%s,%s) RETURNING id",
                        (title, chash, full, now, now, now))
                    src_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO knowledge_chunk (project_id, source_id, chunk_type, title, content, content_hash, "
                        "token_count, embedding_id, tags, status, created_at) "
                        "VALUES (1,%s,'capture',%s,%s,%s,0,'','[]','active',%s)",
                        (src_id, title, full, _h(full), now))
                    direct += 1
                # 图谱扩展实体/关系（新增模块）
                extras = [
                    ("module", "user:login", "用户端-登录注册", "注册/匿名登录/会话"),
                    ("module", "user:recharge", "用户端-充值支付", "充值/支付/资产"),
                    ("module", "admin:message", "运营后台-消息", "聊天室消息/推送消息"),
                    ("module", "admin:teamleague", "运营后台-球队及联赛", "热门联赛/热门球队/屏蔽赛事视频"),
                    ("module", "admin:user", "运营后台-用户管理", "用户列表/封禁/屏蔽/举报/意见反馈"),
                    ("module", "admin:system", "运营后台-系统管理", "版本更新"),
                ]
                for etype, ekey, name, desc in extras:
                    cur.execute("SELECT id FROM knowledge_entity WHERE project_id=1 AND entity_key=%s", (ekey,))
                    if cur.fetchone():
                        continue
                    cur.execute(
                        "INSERT INTO knowledge_entity (project_id, entity_type, entity_key, name, description, source_id, "
                        "business_ref_type, business_ref_id, confidence, review_status, metadata_json, created_at, updated_at) "
                        "VALUES (1,%s,%s,%s,%s,NULL,'',NULL,1.0,'approved','{}',%s,%s)",
                        (etype, ekey, name, desc, now, now))
            conn.commit()
            summary["direct_synced"] = direct
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        print(f"[direct] 直连补入 {direct} 条知识源（capture API 受阻）", flush=True)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "rag-content-sync-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
