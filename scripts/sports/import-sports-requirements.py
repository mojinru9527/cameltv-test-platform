"""体育平台承接 — 功能需求/用例/知识/模块关联一键导入（Batch 102）。

流程: 登录 → 上传需求文档（用户端/运营后台） → AI 提取功能模块 → 确认提取
      → AI 生成功能用例 → 导入用例库 → 创建发布包/模块树 → 知识中心入库
      → 跨系统关联（用户端 ↔ 运营后台 ↔ konfi） → 输出证据 JSON。

运行: <venv-python> scripts/sports/import-sports-requirements.py --password <pw> [--backend-url ...]
凭据: --password 或环境变量 TP_ADMIN_PASSWORD；不回显、不入库。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "产品需求"
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-102"

# (本地文件, 上传文件名/标题, 说明)
REQUIREMENT_DOCS = [
    (
        DOCS_DIR / "蓝湖原型-用户端原型-20260611_180510.md",
        "体育平台-用户端-需求规格说明书.md",
        "用户端原型（98 页）：首页/赛事详情/直播间/我的/UGC/资讯/搜索/PC 端/WEB 端",
    ),
    (
        DOCS_DIR / "蓝湖原型-运营后台-20260611_180605.md",
        "体育平台-运营后台-需求规格说明书.md",
        "运营后台原型（72 页）：财务/赛事预测/UGC/内容/商城/广告/装扮/消息/用户/系统",
    ),
    (
        DOCS_DIR / "更新日志-用户端原型-完整版.md",
        "体育平台-用户端-更新日志.md",
        "用户端更新日志（版本历史）",
    ),
    (
        DOCS_DIR / "更新日志-运营后台-完整版.md",
        "体育平台-运营后台-更新日志.md",
        "运营后台更新日志（版本历史）",
    ),
]


class TpClient:
    def __init__(self, base: str, username: str, password: str, dry_run: bool, origin: str):
        self.base = base.rstrip("/")
        self.username = username
        self.password = password
        self.dry_run = dry_run
        self.origin = origin
        self.headers = {"X-Project-Id": "0", "Origin": origin}
        self.summary: dict = {"backend": self.base, "dry_run": dry_run, "username": username}

    def call(self, method: str, path: str, *, timeout: float = 900, **kw):
        if self.dry_run:
            print(f"[dry-run] {method} {path}", flush=True)
            return _dry_response(method, path)
        r = httpx.request(method, self.base + path, headers=self.headers, timeout=timeout, **kw)
        if r.status_code >= 400:
            body = r.text[:400]
            print(f"ERROR {method} {path} -> {r.status_code}: {body}", flush=True)
            raise SystemExit(1)
        j = r.json()
        if j.get("code") not in (None, 0):
            print(f"ERROR {method} {path} -> code={j.get('code')}: {j.get('msg')}", flush=True)
            raise SystemExit(1)
        return j.get("data", j)

    def login(self):
        if self.dry_run:
            self.headers["Authorization"] = "Bearer dry-run-token"
            self.headers["X-Project-Id"] = "1"
            return 1
        data = self.call("POST", "/auth/login", json={"username": self.username, "password": self.password})
        token = data.get("access_token") or ""
        if not token:
            print("ERROR: 登录未返回 access_token", flush=True)
            raise SystemExit(1)
        self.headers["Authorization"] = f"Bearer {token}"
        projects = self.call("GET", "/projects")
        pid = projects[0]["id"] if projects else 1
        self.headers["X-Project-Id"] = str(pid)
        self.summary["project_id"] = pid
        print(f"[login] ok, project_id={pid}", flush=True)
        return pid

    def list_requirements(self) -> list[dict]:
        if self.dry_run:
            return []
        items: list[dict] = []
        page = 1
        while True:
            data = self.call("GET", f"/requirements?page={page}&page_size=100")
            rows = data.get("items", [])
            items.extend(rows)
            total = data.get("total", 0)
            if page * 100 >= total:
                break
            page += 1
        return items

    def get_requirement(self, doc_id: int) -> dict:
        if self.dry_run:
            return {"id": doc_id, "extraction_status": "confirmed", "ai_raw": "{}"}
        return self.call("GET", f"/requirements/{doc_id}")

    def get_extraction(self, doc_id: int) -> dict:
        if self.dry_run:
            return {"modules": [], "extraction_status": "pending_review"}
        return self.call("GET", f"/requirements/{doc_id}/extraction")

    def upload_doc(self, local_path: Path, upload_name: str, note: str) -> dict:
        if self.dry_run:
            return {"id": 1, "title": upload_name}
        with local_path.open("rb") as fh:
            r = httpx.post(
                self.base + "/requirements/upload",
                headers=self.headers,
                files={"file": (upload_name, fh, "text/markdown")},
                timeout=300,
            )
        if r.status_code >= 400:
            print(f"ERROR upload {upload_name} -> {r.status_code}: {r.text[:400]}", flush=True)
            raise SystemExit(1)
        j = r.json()
        if j.get("code") not in (None, 0):
            print(f"ERROR upload {upload_name} -> code={j.get('code')}: {j.get('msg')}", flush=True)
            raise SystemExit(1)
        doc = j["data"]
        self.summary.setdefault("requirements", []).append({
            "id": doc["id"], "title": doc["title"], "note": note,
        })
        print(f"[upload] id={doc['id']} title={doc['title']} note={note}", flush=True)
        return doc

    def extract_with_retry(self, doc_id: int, title: str, attempts: int = 3) -> dict:
        if self.dry_run:
            return {"modules": [], "extraction_status": "pending_review"}
        for i in range(1, attempts + 1):
            print(f"[extract] doc={doc_id} 第 {i}/{attempts} 次提取中（AI，约 3-6 分钟）...", flush=True)
            try:
                result = self.call("POST", f"/requirements/{doc_id}/extract", timeout=900)
                modules = result.get("modules") or []
                print(f"[extract] doc={doc_id} modules={len(modules)}", flush=True)
                return result
            except SystemExit:
                if i < attempts:
                    print(f"[extract] doc={doc_id} 第 {i} 次失败，等待 20s 后重试...", flush=True)
                    time.sleep(20)
                    continue
                raise
        return {}

    def confirm_extraction(self, doc_id: int, title: str) -> dict:
        if self.dry_run:
            return {"ok": True}
        extraction = self.get_extraction(doc_id)
        modules = extraction.get("modules") or []
        status = extraction.get("extraction_status", "")
        if status == "confirmed":
            print(f"[confirm] doc={doc_id} 已确认，跳过", flush=True)
            return {"ok": True, "skipped": True}
        confirmed = self.call("POST", f"/requirements/{doc_id}/extraction/confirm", json={
            "action": "confirm",
            "modules": modules,
        }, timeout=300)
        print(f"[confirm] doc={doc_id} {confirmed}", flush=True)
        return confirmed

    def generate_cases(self, doc_id: int, title: str) -> list[dict]:
        if self.dry_run:
            return [{"index": 1, "title": "示例功能用例", "domain": "体育平台-用户端", "module": "首页"}]
        print(f"[generate] doc={doc_id} 生成功能用例中（AI 分批，可等待数分钟）...", flush=True)
        for i in range(1, 4):
            try:
                result = self.call("POST", f"/requirements/{doc_id}/generate", json={"use_extraction": True}, timeout=1800)
                break
            except SystemExit:
                if i < 3:
                    print(f"[generate] doc={doc_id} 第 {i} 次失败，等待 20s 后重试...", flush=True)
                    time.sleep(20)
                    continue
                raise
        cases = result.get("functional_cases") or []
        print(f"[generate] doc={doc_id} functional_cases={len(cases)}", flush=True)
        return cases

    def import_cases(self, doc_id: int, cases: list[dict], create_plan: bool = False) -> dict:
        if self.dry_run:
            return {"imported": 1, "skipped": 0, "total": 1}
        indices = [c.get("index", i + 1) for i, c in enumerate(cases)]
        if not indices:
            return {"imported": 0, "skipped": 0, "total": 0}
        result = self.call("POST", f"/requirements/{doc_id}/import", json={
            "indices": indices, "edited_cases": [], "create_plan": create_plan,
        }, timeout=900)
        print(f"[import] doc={doc_id} {result}", flush=True)
        return result

    def ensure_domain(self, domain: str, modules: list[str]) -> dict:
        """确保用例域存在；返回 domains 列表。"""
        if self.dry_run:
            return {"domain": domain, "modules": modules}
        domains = self.call("GET", "/test-cases/domains")
        existing = next((d for d in domains if d.get("domain") == domain), None)
        if not existing:
            created = self.call("POST", "/test-cases/domains", json={"domain": domain})
            print(f"[domain] created {domain} -> {created}", flush=True)
        else:
            print(f"[domain] exists {domain}", flush=True)
        return {"domain": domain, "modules": modules}

    def create_release_bundle(self, name: str, client_version: str, admin_version: str, desc: str) -> dict:
        if self.dry_run:
            return {"id": 1, "name": name}
        bundles = self.call("GET", "/release-bundles")
        items = bundles.get("items", bundles if isinstance(bundles, list) else [])
        existing = next((b for b in items if b.get("name") == name), None)
        if existing:
            print(f"[bundle] exists id={existing['id']} {name}", flush=True)
            return existing
        created = self.call("POST", "/release-bundles", json={
            "name": name, "description": desc,
            "client_version": client_version, "admin_version": admin_version,
        })
        print(f"[bundle] created id={created['id']} {name}", flush=True)
        return created

    def knowledge_capture(self, title: str, content: str) -> dict:
        if self.dry_run:
            return {"id": 1}
        result = self.call("POST", "/knowledge/capture", json={"title": title, "content": content}, timeout=300)
        print(f"[knowledge] captured {title}", flush=True)
        return result

    def save_evidence(self):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        out = EVIDENCE_DIR / "sports-functional-import-summary.json"
        out.write_text(json.dumps(self.summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[evidence] saved: {out}", flush=True)


def _dry_response(method: str, path: str):
    if path == "/auth/login":
        return {"access_token": "dry-run-token"}
    if path == "/projects":
        return [{"id": 1}]
    if path.startswith("/requirements?") or path == "/requirements":
        return {"items": [], "total": 0}
    if path.startswith("/requirements/upload"):
        return {"id": 1, "title": "dry-run"}
    if path.endswith("/extract"):
        return {"modules": [{"id": "MOD-1", "name": "示例模块", "description": "", "function_points": []}]}
    if path.endswith("/extraction/confirm"):
        return {"ok": True}
    if path.endswith("/generate"):
        return {"functional_cases": [{"index": 1, "title": "示例", "domain": "体育平台-用户端", "module": "首页"}]}
    if path.endswith("/import"):
        return {"imported": 1, "skipped": 0, "total": 1}
    if path == "/test-cases/domains":
        return []
    if path.startswith("/release-bundles") and method == "POST":
        return {"id": 1, "name": "dry-run"}
    if path == "/release-bundles":
        return {"items": []}
    if path == "/knowledge/capture":
        return {"id": 1}
    return {"ok": True}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--origin", default="https://cameltv-test-platform1.vercel.app")
    ap.add_argument("--docs-only", action="store_true", help="只上传需求文档并提取确认")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password 或环境变量 TP_ADMIN_PASSWORD", flush=True)
        return 1

    client = TpClient(args.backend_url, args.username, args.password, args.dry_run, args.origin)
    client.login()

    # 1) 需求文档上传 + 提取确认
    existing = {r.get("title"): r for r in client.list_requirements()}
    for local_path, upload_name, note in REQUIREMENT_DOCS:
        if not local_path.exists():
            print(f"WARN 文档缺失: {local_path}", flush=True)
            continue
        title = Path(upload_name).stem
        prev = existing.get(title)
        if prev:
            doc = client.get_requirement(prev["id"])
            print(f"[doc] 已存在 id={prev['id']} title={title} extraction={doc.get('extraction_status')}", flush=True)
        else:
            doc = client.upload_doc(local_path, upload_name, note)
        status = doc.get("extraction_status", "not_started")
        if status == "not_started":
            client.extract_with_retry(doc["id"], doc.get("title", upload_name))
        elif status == "pending_review":
            print(f"[extract] doc={doc['id']} 已有提取结果（pending_review），直接确认", flush=True)
        elif status == "confirmed":
            print(f"[extract] doc={doc['id']} 已确认，跳过", flush=True)
        client.confirm_extraction(doc["id"], doc.get("title", upload_name))
    client.save_evidence()
    print("[done] 需求文档导入+提取完成（AI 生成用例需在平台页面确认提取结果后执行）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
