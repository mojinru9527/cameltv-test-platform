"""体育平台承接 — Wiki 知识库基线建立（Batch 110，C102-3 直建能力落地）。

流程：
  1) 平台 API 读取需求文档提取结果（modules + function_points）
  2) 直连生产库建 ReleaseBundle（active）+ RequirementModule 树
     （platform: APP/PC/WEB/ADMIN → module → page → function_point）+ ModuleAdminLink
  3) 调 /wiki/sync/bundle/{id}（create_wiki_pages=true）→ WikiRawSource
  4) 逐 raw source 建 /wiki/ingest-jobs → 编译 WikiPage
  5) 审批 /wiki/pages/{id}/approve（draft→approved）
  6) 建 /wiki/diff/tasks（platform_rag vs platform_wiki，按核心模块 query）
  7) 输出证据 JSON（wiki-baseline-summary.json）

运行: <venv-python> scripts/sports/build-wiki-baseline.py --password <pw> --database-url "$env:TP_DATABASE_URL"
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
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110"

BUNDLE_NAME = "体育平台-需求基线"
BUNDLE_DESC = "Batch 110 由需求文档提取结果直建（C102-3 落地）：用户端 14.1.0 / 运营后台 8.2.0"

DIFF_QUERIES = ["首页", "赛事详情", "直播间", "资讯", "搜索", "我的", "回放", "世界杯", "财务管理", "UGC"]


def _api(base: str, username: str, password: str) -> httpx.Client:
    c = httpx.Client(
        base_url=base.rstrip("/"),
        timeout=120,
        headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"},
    )
    r = c.post("/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"
    return c


def _platform_for_doc(doc_title: str) -> str:
    if "运营后台" in doc_title:
        return "ADMIN"
    return "APP"  # 用户端（App/PC/Web 以 APP 为首要平台，其余可后续扩展）


def _ensure_bundle(cur, project_id: int) -> int:
    cur.execute(
        "SELECT id FROM release_bundle WHERE project_id=%s AND name=%s AND status='active'",
        (project_id, BUNDLE_NAME),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO release_bundle (project_id, name, description, client_version, admin_version, status, created_at, updated_at) "
        "VALUES (%s,%s,%s,'14.1.0','8.2.0','active',now(),now()) RETURNING id",
        (project_id, BUNDLE_NAME, BUNDLE_DESC),
    )
    return cur.fetchone()[0]


def _node_id(cur, bundle_id: int, name: str, platform: str) -> int | None:
    cur.execute(
        "SELECT id FROM requirement_module WHERE release_bundle_id=%s AND name=%s AND platform=%s LIMIT 1",
        (bundle_id, name, platform),
    )
    row = cur.fetchone()
    return row[0] if row else None


def build_tree(dsn: str, client: httpx.Client, doc_ids: list[int]) -> dict:
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    result = {"bundles": 0, "modules": 0, "pages": 0, "fps": 0, "links": 0}
    try:
        with conn.cursor() as cur:
            bundle_id = _ensure_bundle(cur, 1)
            result["bundles"] = 1
            for doc_id in doc_ids:
                doc = client.get(f"/requirements/{doc_id}").json()["data"]
                ext = client.get(f"/requirements/{doc_id}/extraction").json()["data"]
                platform = _platform_for_doc(doc.get("title") or "")
                root_id = _node_id(cur, bundle_id, platform, platform)
                if not root_id:
                    cur.execute(
                        "INSERT INTO requirement_module (project_id, release_bundle_id, name, node_type, platform, "
                        "parent_module_id, source_version, change_type, description, sort_order, created_at, updated_at) "
                        "VALUES (1,%s,%s,'module',%s,NULL,%s,'new','',0,now(),now()) RETURNING id",
                        (bundle_id, platform, platform, doc.get("version") or "14.1.0"),
                    )
                    root_id = cur.fetchone()[0]
                    result["modules"] += 1
                for m in ext.get("modules") or []:
                    mod_name = (m.get("name") or "").strip()
                    if not mod_name:
                        continue
                    mod_id = _node_id(cur, bundle_id, mod_name, platform)
                    if not mod_id:
                        cur.execute(
                            "INSERT INTO requirement_module (project_id, release_bundle_id, name, node_type, platform, "
                            "parent_module_id, source_version, change_type, description, sort_order, created_at, updated_at) "
                            "VALUES (1,%s,%s,'module',%s,%s,%s,'new',%s,0,now(),now()) RETURNING id",
                            (bundle_id, mod_name, platform, root_id, "14.1.0", (m.get("description") or "")[:2000]),
                        )
                        mod_id = cur.fetchone()[0]
                        result["modules"] += 1
                    page_id = _node_id(cur, bundle_id, f"{mod_name}-页面", platform)
                    if not page_id:
                        cur.execute(
                            "INSERT INTO requirement_module (project_id, release_bundle_id, name, node_type, platform, "
                            "parent_module_id, source_version, change_type, description, sort_order, created_at, updated_at) "
                            "VALUES (1,%s,%s,'page',%s,%s,%s,'new',%s,1,now(),now()) RETURNING id",
                            (bundle_id, f"{mod_name}-页面", platform, mod_id, "14.1.0", (m.get("description") or "")[:4000]),
                        )
                        page_id = cur.fetchone()[0]
                        result["pages"] += 1
                    for fp in m.get("function_points") or []:
                        fp_name = (fp.get("name") or fp.get("content") or "").strip()
                        if not fp_name:
                            continue
                        if _node_id(cur, bundle_id, fp_name, platform):
                            continue
                        cur.execute(
                            "INSERT INTO requirement_module (project_id, release_bundle_id, name, node_type, platform, "
                            "parent_module_id, source_version, change_type, description, sort_order, created_at, updated_at) "
                            "VALUES (1,%s,%s,'function_point',%s,%s,%s,'new',%s,2,now(),now())",
                            (bundle_id, fp_name[:500], platform, page_id, "14.1.0", (fp.get("content") or "")[:2000]),
                        )
                        result["fps"] += 1
            conn.commit()
        result["bundle_id"] = bundle_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--database-url", default=os.environ.get("TP_DATABASE_URL", ""))
    ap.add_argument("--doc-ids", default="1,2,3,4")
    args = ap.parse_args()
    if not args.password or not args.database_url:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD 与 --database-url / TP_DATABASE_URL", flush=True)
        return 1

    client = _api(args.backend_url, args.username, args.password)
    summary: dict = {"tree": None, "wiki": None, "errors": []}

    try:
        summary["tree"] = build_tree(args.database_url, client, [int(x) for x in args.doc_ids.split(",") if x.strip()])
        bundle_id = summary["tree"]["bundle_id"]
        print(f"[tree] bundle={bundle_id} {summary['tree']}", flush=True)
    except Exception as exc:
        summary["errors"].append(f"build_tree: {exc}")
        print(f"[tree] FAILED: {exc}", flush=True)
        bundle_id = None

    if bundle_id:
        # 3) Wiki 同步（依赖 WIKI_ENABLED）
        try:
            r = client.post(f"/wiki/sync/bundle/{bundle_id}", json={"create_wiki_pages": True})
            j = r.json()
            if r.status_code >= 400 or j.get("code") not in (None, 0):
                raise RuntimeError(f"sync 503/错误: {r.status_code} {j.get('msg')}")
            summary["wiki"] = {"sync": j.get("data")}
            print(f"[wiki] sync={j.get('data')}", flush=True)
        except Exception as exc:
            summary["errors"].append(f"wiki_sync: {exc}")
            print(f"[wiki] sync FAILED: {exc}（WIKI_ENABLED 未启用或模块树为空）", flush=True)

        if summary.get("wiki"):
            # 4) 编译 raw sources → WikiPage
            try:
                raw = client.get("/wiki/raw-sources", params={"source_type": "requirement", "page_size": 200}).json().get("data", {})
                raws = raw.get("items") or []
                jobs = []
                for rs in raws:
                    job = client.post("/wiki/ingest-jobs", json={"raw_source_id": rs["id"]}).json().get("data", {})
                    jobs.append(job)
                time.sleep(3)
                jobs_done = []
                for job in jobs:
                    jid = job.get("id")
                    for _ in range(60):
                        st = client.get(f"/wiki/ingest-jobs/{jid}").json().get("data", {})
                        if st.get("status") in ("success", "failed"):
                            jobs_done.append(st)
                            break
                        time.sleep(3)
                summary["wiki"]["ingest_jobs"] = jobs_done
                print(f"[wiki] ingest jobs={len(jobs_done)}", flush=True)
            except Exception as exc:
                summary["errors"].append(f"wiki_ingest: {exc}")
                print(f"[wiki] ingest FAILED: {exc}", flush=True)

            # 5) 审批 WikiPage
            try:
                pages = client.get("/wiki/pages", params={"page_size": 200}).json().get("data", {})
                approved = 0
                for pg in pages.get("items") or []:
                    if pg.get("review_status") in ("approved",):
                        approved += 1
                        continue
                    client.post(f"/wiki/pages/{pg['id']}/approve", json={"comment": "Batch 110 wiki baseline"})
                    approved += 1
                summary["wiki"]["approved_pages"] = approved
                print(f"[wiki] approved pages={approved}", flush=True)
            except Exception as exc:
                summary["errors"].append(f"wiki_approve: {exc}")
                print(f"[wiki] approve FAILED: {exc}", flush=True)

            # 6) 差异对比（RAG vs Wiki）
            try:
                diff_tasks = []
                for q in DIFF_QUERIES:
                    task = client.post("/wiki/diff/tasks", json={
                        "title": f"体育平台-{q}（RAG vs Wiki）",
                        "compare_type": "kb",
                        "left_kb_type": "platform_rag",
                        "right_kb_type": "platform_wiki",
                        "query": q,
                    }).json().get("data", {})
                    diff_tasks.append({"query": q, "task_id": task.get("id")})
                summary["wiki"]["diff_tasks"] = diff_tasks
                print(f"[wiki] diff tasks={len(diff_tasks)}", flush=True)
            except Exception as exc:
                summary["errors"].append(f"wiki_diff: {exc}")
                print(f"[wiki] diff FAILED: {exc}", flush=True)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "wiki-baseline-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
