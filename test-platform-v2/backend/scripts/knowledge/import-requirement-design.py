# -*- coding: utf-8 -*-
"""需求/设计稿入库脚本（Batch 124 / C124-1 / C124-3）。

读取蓝湖导出目录（hierarchy.json + HTML 页面 + images/ 设计稿截图），
通过平台 POST /knowledge/design-assets/import 逐批入库（文本 + 图片 base64，幂等）。

用法（在生产服务器或可访问生产 API 的环境）:
    python scripts/knowledge/import-requirement-design.py \
        --export-dir ../data/lanhu-exports/运营后台原型 \
        --password <TP_ADMIN_PASSWORD> [--dry-run] [--limit 20] [--filter 赛事预测]

凭据: --password 或环境变量 TP_ADMIN_PASSWORD；不回显、不入库。
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_EXPORT = REPO_ROOT / "test-platform-v2" / "backend" / "data" / "lanhu-exports" / "运营后台原型"


def extract_page_text(html_path: Path) -> str:
    """从蓝湖导出 HTML 提取页面可见文本（去 script/style/标签）。"""
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
    raw = re.sub(r"<style.*?</style>", "", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    text = html.unescape(raw)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)


def load_hierarchy(export_dir: Path) -> list[dict]:
    hier = export_dir / "hierarchy.json"
    if not hier.exists():
        print(f"未找到 hierarchy.json: {hier}", file=sys.stderr)
        sys.exit(1)
    return json.loads(hier.read_text(encoding="utf-8"))


def build_sources(export_dir: Path, nodes: list[dict], page_filter: str = "", limit: int = 0) -> list[dict]:
    images_root = export_dir / "images"
    sources: list[dict] = []
    skipped_no_file = 0
    for n in nodes:
        if n.get("type") != "page":
            continue
        pid = n.get("lanhu_page_id") or ""
        if not pid:
            continue
        if page_filter and page_filter not in n.get("path", ""):
            continue
        html_path = export_dir / pid
        if not html_path.exists():
            skipped_no_file += 1
            print(f"[skip] 缺 HTML: {pid}", flush=True)
            continue
        text = extract_page_text(html_path)
        basename = pid[: -len(".html")] if pid.endswith(".html") else pid
        img_dir = images_root / basename
        shots: list[str] = n.get("screenshots") or []
        images = []
        for fname in shots:
            fp = img_dir / fname
            if not fp.is_file():
                continue
            images.append({"filename": fname, "base64": base64.b64encode(fp.read_bytes()).decode("ascii")})
        sources.append(
            {
                "title": basename,
                "source_ref": n.get("path", ""),
                "text": text,
                "metadata": {"lanhu_page_id": pid, "path": n.get("path", ""), "images": shots},
                "images": images,
            }
        )
        if limit and len(sources) >= limit:
            break
    print(f"[build] sources={len(sources)} (缺 HTML 跳过 {skipped_no_file})", flush=True)
    return sources


def call_import(client: httpx.Client, base: str, headers: dict, batch: list[dict], dry_run: bool) -> dict:
    if dry_run:
        print(f"[dry-run] POST /knowledge/design-assets/import batch={len(batch)}", flush=True)
        return {"created_sources": len(batch), "skipped_sources": 0, "created_chunks": len(batch), "saved_images": sum(len(s["images"]) for s in batch)}
    r = client.post(
        base + "/knowledge/design-assets/import",
        headers=headers,
        json={"sources": batch},
        timeout=600,
    )
    if r.status_code >= 400:
        print(f"ERROR import -> {r.status_code}: {r.text[:500]}", flush=True)
        sys.exit(1)
    j = r.json()
    if j.get("code") not in (None, 0):
        print(f"ERROR import -> code={j.get('code')}: {j.get('msg')}", flush=True)
        sys.exit(1)
    return j.get("data", j)


def main() -> int:
    ap = argparse.ArgumentParser(description="需求/设计稿入库（蓝湖导出 → design-assets）")
    ap.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT)
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://swiftbugs.cn/api/v1"))
    ap.add_argument("--username", default=os.environ.get("TP_ADMIN_USER", "admin"))
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--dry-run", action="store_true", help="只打印不请求")
    ap.add_argument("--limit", type=int, default=0, help="最多导入 N 页（0=全部）")
    ap.add_argument("--filter", default="", help="只导入 path 含该子串的页")
    ap.add_argument("--batch-size", type=int, default=5)
    args = ap.parse_args()

    if not args.password and not args.dry_run:
        print("缺少 --password 或环境变量 TP_ADMIN_PASSWORD", file=sys.stderr)
        return 1

    export_dir: Path = args.export_dir.resolve()
    nodes = load_hierarchy(export_dir)
    sources = build_sources(export_dir, nodes, args.filter, args.limit)
    if not sources:
        print("没有可导入的页面", file=sys.stderr)
        return 1

    base = args.backend_url.rstrip("/")
    headers = {"X-Project-Id": "0", "Origin": "https://swiftbugs.cn"}
    if not args.dry_run:
        with httpx.Client(timeout=120) as client:
            r = client.post(base + "/auth/login", json={"username": args.username, "password": args.password})
            r.raise_for_status()
            j = r.json()
            data = j.get("data", j)
            token = data.get("access_token") or j.get("access_token", "")
            if not token:
                print("ERROR: 登录未返回 access_token", file=sys.stderr)
                return 1
            headers["Authorization"] = f"Bearer {token}"
            rp = client.get(base + "/projects", headers=headers)
            rp.raise_for_status()
            projects = rp.json().get("data", [])
            pid = projects[0]["id"] if projects else 1
            headers["X-Project-Id"] = str(pid)
            print(f"[login] ok, project_id={pid}", flush=True)

    total_images = sum(len(s["images"]) for s in sources)
    print(f"[import] pages={len(sources)} images={total_images} batch={args.batch_size}", flush=True)
    summary = {"export_dir": str(export_dir), "pages": len(sources), "images": total_images, "dry_run": args.dry_run, "batches": []}
    with httpx.Client(timeout=600) as client:
        for i in range(0, len(sources), args.batch_size):
            batch = sources[i : i + args.batch_size]
            res = call_import(client, base, headers, batch, args.dry_run)
            summary["batches"].append(res)
            print(f"[batch {i // args.batch_size + 1}] {res}", flush=True)

    out = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-124" / "design-assets-import-summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] summary → {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
