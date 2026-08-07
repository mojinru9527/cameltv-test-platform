"""体育平台承接 — 页面 XHR 批量采集（B10/C103-5，含请求头）。

用 Playwright 只读打开目标页面，拦截 request（method/url/headers/body）+ response（状态/body 前 250KB），
产出样本 JSON（含请求头——batch-112 校准暴露的缺口），供接口用例基线（C103-3/4）使用。
只读口径：仅 GET/HEAD + 查询型 POST（复用 B112-4 守卫）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-115"
BASE_URL = "https://www.camel1.tv"

# 只读查询型 POST（同 production-p0-contract READONLY_POST_PATTERNS）
READONLY_POST = [
    "/ee/ads/activity/get", "/ee/search/", "/ee/news/", "/ee/client/",
    "/login/anonymous/web", "/konfi-service/web/getDataById",
    "/ee/sports_live/", "/ee/setting",
]
WRITE_MARKERS = ["pay", "order", "refund", "recharge", "withdraw", "deposit",
                 "favorite", "like", "comment", "review", "create", "save",
                 "update", "delete", "add", "remove", "send", "publish", "bonus", "gift", "diamond"]

PAGES = ["/", "/q/news", "/search", "/my", "/match-replay", "/worldcup-2026",
         "/r/league/UEFA%20Europa%20League", "/football/as-monaco-vs-getafe/n54qllhn0vwjqvy",
         "/football/as-monaco-vs-getafe/n54qllhn0vwjqvy/live/2y8m4zh5kwgpql0"]


def _allowed(method: str, url: str) -> bool:
    m = method.upper()
    if m in ("GET", "HEAD"):
        return True
    if m != "POST":
        return False
    path = url.split("?")[0]
    if any(w in path.lower() for w in WRITE_MARKERS):
        return False
    return any(p in path for p in READONLY_POST)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--headless", action="store_true", default=True)
    args = ap.parse_args()

    samples: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless,
                                     args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"])
        page = browser.new_page()

        def on_request(req):
            if not _allowed(req.method, req.url):
                return
            headers = dict(req.headers)
            headers.pop("authorization", None)
            headers.pop("cookie", None)
            body = ""
            try:
                if req.method in ("POST", "PUT", "PATCH"):
                    body = (req.post_data or "")[:4000]
            except Exception:
                pass
            req._captured = {
                "method": req.method, "url": req.url, "headers": headers, "body": body,
            }

        def on_response(resp):
            cap = getattr(resp.request, "_captured", None)
            if not cap:
                return
            try:
                body = resp.text()[:250000]
            except Exception:
                body = ""
            samples.append({**cap, "status": resp.status, "response": body})

        page.on("request", on_request)
        page.on("response", on_response)
        for path in args.pages.split(","):
            path = path.strip()
            if not path:
                continue
            try:
                page.goto(BASE_URL + path, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                print(f"[capture] {path} -> {len(samples)} samples so far", flush=True)
            except Exception as e:
                print(f"[capture] {path} ERROR {e}", flush=True)
        browser.close()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "xhr-capture-sample.json"
    out.write_text(json.dumps({"base": BASE_URL, "pages": args.pages.split(","), "samples": samples},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] samples={len(samples)} -> {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())