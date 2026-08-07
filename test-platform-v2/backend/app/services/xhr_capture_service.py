"""C115-3 — 页面 XHR 采集服务（平台 API 集成，B10/C103-5 落地）。

后台线程执行只读 Playwright 采集（复用 capture-page-xhr.py 口径：GET/HEAD + 查询型 POST，
含请求头），样本 JSON 存 backend/storage/xhr-capture/{id}.json，供用例基线回填（C103-3/4）。
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

from app.core.config import settings

_STORAGE = Path(settings.storage_dir) / "xhr-capture" if getattr(settings, "storage_dir", None) else Path("storage") / "xhr-capture"
_TASKS: dict[str, dict] = {}
_LOCK = threading.Lock()

# 只读查询型 POST（同 production-p0-contract READONLY_POST_PATTERNS）
_READONLY_POST = ["/ee/ads/activity/get", "/ee/search/", "/ee/news/", "/ee/client/",
                  "/login/anonymous/web", "/konfi-service/web/getDataById",
                  "/ee/sports_live/", "/ee/setting"]
_WRITE_MARKERS = ["pay", "order", "refund", "recharge", "withdraw", "deposit", "favorite",
                  "like", "comment", "review", "create", "save", "update", "delete", "add",
                  "remove", "send", "publish", "bonus", "gift", "diamond"]


def _allowed(method: str, url: str) -> bool:
    m = method.upper()
    if m in ("GET", "HEAD"):
        return True
    if m != "POST":
        return False
    path = url.split("?")[0]
    if any(w in path.lower() for w in _WRITE_MARKERS):
        return False
    return any(p in path for p in _READONLY_POST)


def create_capture_task(*, pages: list[str], project_id: int) -> dict:
    task_id = f"cap-{uuid.uuid4().hex[:10]}"
    with _LOCK:
        _TASKS[task_id] = {"id": task_id, "status": "running", "project_id": project_id,
                           "pages": pages, "sample_count": 0, "file": "", "error": "", "created_at": time.time()}
    thread = threading.Thread(target=_run, args=(task_id, pages), daemon=True)
    thread.start()
    return _TASKS[task_id]


def get_task(task_id: str) -> dict | None:
    with _LOCK:
        return _TASKS.get(task_id)


def _run(task_id: str, pages: list[str]) -> None:
    try:
        from playwright.sync_api import sync_playwright
        samples: list[dict] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu"])
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
                req._cap = {"method": req.method, "url": req.url, "headers": headers, "body": body}

            def on_response(resp):
                cap = getattr(resp.request, "_cap", None)
                if not cap:
                    return
                try:
                    rbody = resp.text()[:250000]
                except Exception:
                    rbody = ""
                samples.append({**cap, "status": resp.status, "response": rbody})

            page.on("request", on_request)
            page.on("response", on_response)
            for path in pages:
                try:
                    page.goto(path if path.startswith("http") else "https://www.camel1.tv" + path,
                              wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(1500)
                except Exception as exc:
                    pass
            browser.close()

        _STORAGE.mkdir(parents=True, exist_ok=True)
        out = _STORAGE / f"{task_id}.json"
        out.write_text(json.dumps({"task_id": task_id, "pages": pages, "samples": samples},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
        with _LOCK:
            _TASKS[task_id].update({"status": "done", "sample_count": len(samples), "file": str(out)})
    except Exception as exc:
        with _LOCK:
            _TASKS[task_id].update({"status": "failed", "error": str(exc)[:300]})