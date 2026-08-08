"""Batch 124 — 需求/设计稿入库（HTML 原型页 → 文本+图片 → 平台知识源，幂等）。

读取 axure_extract 目录下每个 HTML 页：提取功能点文本 + 收集 images/<页>/ 设计稿图片，
POST 到 /knowledge/design-assets/import（按 content_hash 去重）。

运行: TP_ADMIN_PASSWORD=<pwd> <python> scripts/knowledge/import-requirement-design.py \
        --source-dir F:/CamelTv/test-platform-v2/backend/data/axure_extract_test [--backend-url <url>] [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

import httpx

USERNAME = "sportsadmin"
BATCH = 5


def extract_text(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", "\n", raw)
    txt = html.unescape(txt)
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True, help="axure_extract 目录（含 *.html 与 images/）")
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 页（0=全部）")
    ap.add_argument("--filter", default="", help="只处理页面名包含该关键词的页")
    args = ap.parse_args()

    root = Path(args.source_dir)
    pages = sorted(root.glob("*.html"))
    if args.filter:
        pages = [p for p in pages if args.filter in p.stem]
    if args.limit:
        pages = pages[: args.limit]
    print(f"[req-import] HTML 页 {len(pages)} 个", flush=True)

    sources = []
    for hp in pages:
        text = extract_text(hp.read_text(encoding="utf-8", errors="ignore"))
        img_dir = root / "images" / hp.stem
        images = []
        if img_dir.is_dir():
            for img in sorted(img_dir.iterdir()):
                if img.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"):
                    continue
                data = img.read_bytes()
                if len(data) > 6 * 1024 * 1024:
                    continue
                images.append({"filename": img.name, "base64": base64.b64encode(data).decode("ascii")})
        sources.append({
            "title": hp.stem,
            "source_ref": hp.name,
            "text": text,
            "metadata": {"source_dir": root.name, "html_file": hp.name, "image_count": len(images)},
            "images": images,
        })

    total_text = sum(len(s["text"]) for s in sources)
    total_img = sum(len(s["images"]) for s in sources)
    print(f"[req-import] 文本字符 {total_text}；设计稿图片 {total_img} 张；平均每页 {total_img/max(1,len(sources)):.1f} 张", flush=True)
    if args.dry_run:
        return 0
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=300,
                      headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"}) as client:
        r = client.post("/auth/login", json={"username": USERNAME, "password": args.password})
        r.raise_for_status()
        client.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"
        created = skipped = images = 0
        for i in range(0, len(sources), BATCH):
            chunk = sources[i : i + BATCH]
            rr = client.post("/knowledge/design-assets/import", json={"sources": chunk})
            rr.raise_for_status()
            d = rr.json()["data"]
            created += d["created_sources"]
            skipped += d["skipped_sources"]
            images += d["saved_images"]
            print(f"[req-import] ...批 {i//BATCH+1} 完成（created 累计 {created} / images {images}）", flush=True)
        print(f"[req-import] DONE created={created} skipped={skipped} images={images}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
