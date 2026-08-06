"""运营后台（admcamel.camel1.tv）只读走查（Batch 110）。

纯 HTTP 驱动（httpx + cookie 会话）：
  uuid → 验证码 → /captcha/check → 短信 → /login → /nav → 逐模块页面只读采集
  （跳过「系统」模块，用户明确要求）。
外部协调文件：
  CAPTCHA_ANSWER_FILE（agent 写入识图结果） / SMS_ANSWER_FILE（用户短信码）
状态输出 STATE_FILE；证据输出 evidence/batch-110/admin-walkthrough/。
"""
from __future__ import annotations

import json
import os
import random
import re
import string
import time
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "admin-walkthrough"
TMP = Path(os.environ.get("TEMP", "/tmp"))
STATE = Path(os.environ.get("STATE_FILE", TMP / "admin-walk-state.json"))
CAPTCHA_ANSWER = Path(os.environ.get("CAPTCHA_ANSWER_FILE", TMP / "admin-captcha-answer.txt"))
SMS_ANSWER = Path(os.environ.get("SMS_ANSWER_FILE", TMP / "admin-sms-answer.txt"))
BASE = "https://admcamel.camel1.tv"
USER = os.environ.get("ADMIN_USER", "mojinru")


def set_state(**kw):
    payload = {**kw, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[state]", json.dumps(payload, ensure_ascii=False), flush=True)


def wait_file(f: Path, timeout_s: int, label: str) -> str | None:
    start = time.time()
    while time.time() - start < timeout_s:
        if f.exists():
            v = f.read_text(encoding="utf-8").strip()
            if v:
                return v
        time.sleep(1.5)
    return None


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    uuid = "".join(random.choices(string.ascii_lowercase + string.digits, k=32))
    c = httpx.Client(base_url=BASE, timeout=45, follow_redirects=False)

    # 1) 验证码
    set_state(step="captcha_ready", uuid=uuid)
    r = c.get(f"/captcha/generate?uuid={uuid}&random={random.random()}")
    (EVIDENCE / "captcha-v2.png").write_bytes(r.content)
    code = wait_file(CAPTCHA_ANSWER, 1800, "captcha")
    if not code:
        set_state(step="captcha_timeout")
        return 1
    set_state(step="checking_captcha")
    r = c.post("/captcha/check", data={"userCode": USER, "imageVerifyCode": code, "uuid": uuid})
    print("[captcha/check]", r.text[:200], flush=True)
    if not r.json().get("success"):
        set_state(step="captcha_rejected", resp=r.text[:200])
        return 1

    # 2) 短信
    set_state(step="sms_ready", msg="短信已发送，等待用户提供验证码")
    sms = wait_file(SMS_ANSWER, 3600, "sms")
    if not sms:
        set_state(step="sms_timeout")
        return 1
    r = c.post("/login", data={"smsCode": sms, "userCode": USER})
    print("[login]", r.text[:200], flush=True)
    if not r.json().get("success"):
        set_state(step="login_rejected", resp=r.text[:200])
        return 1
    set_state(step="login_ok")

    # 3) 菜单（多策略：referer / Accept / 跟随重定向）
    menu = []
    nav_debug = {}
    strategies = [
        {"headers": {"Referer": BASE + "/main", "Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}, "follow": True},
        {"headers": {"Referer": BASE + "/main", "Accept": "application/json"}, "follow": True},
        {"headers": {"Referer": BASE + "/main"}, "follow": False},
        {"headers": {}, "follow": True},
    ]
    for i, strat in enumerate(strategies):
        try:
            rr = c.get("/nav", headers=strat["headers"], follow_redirects=strat["follow"])
            head = rr.text[:120].replace("\n", " ")
            nav_debug[f"s{i}"] = {"status": rr.status_code, "final_url": str(rr.url), "len": len(rr.text), "head": head}
            print(f"[nav:s{i}] status={rr.status_code} len={len(rr.text)} head={head}", flush=True)
            try:
                j = rr.json()
                if j.get("success") and j.get("items"):
                    menu = j["items"]
                    (EVIDENCE / "nav.json").write_text(rr.text, encoding="utf-8")
                    break
            except Exception:
                pass
        except Exception as exc:
            nav_debug[f"s{i}"] = {"error": str(exc)[:200]}
            print(f"[nav:s{i}] ERR {exc}", flush=True)
    (EVIDENCE / "nav-debug.json").write_text(json.dumps(nav_debug, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[nav] modules:", len(menu), flush=True)
    if not menu:
        set_state(step="nav_failed", nav_debug=nav_debug)
        return 1

    # 4) 逐模块只读采集（跳过「系统」）
    modules = []
    for m in menu:
        title = m.get("title", "")
        if "系统" in title or "system" in title.lower():
            continue
        children = m.get("children") or []
        mod = {"title": title, "icon": m.get("icon", ""), "pages": []}
        for ch in children:
            href = ch.get("href", "")
            page = {"title": ch.get("title", ""), "href": href}
            if href and href.startswith("/"):
                try:
                    pr = c.get(href)
                    page["status"] = pr.status_code
                    # 页面 HTML 中的 ajax 端点
                    apis = set(re.findall(r"url\s*:\s*['\"]([^'\"]+)['\"]", pr.text))
                    apis |= set(re.findall(r"['\"](/ee/admin/[^'\"]+)['\"]", pr.text))
                    page["apis"] = sorted(apis)[:30]
                    page["html_len"] = len(pr.text)
                    (EVIDENCE / "pages" / f"{re.sub(r'[^\\w\\u4e00-\\u9fa5-]', '_', title)}__{re.sub(r'[^\\w\\u4e00-\\u9fa5-]', '_', ch.get('title',''))[:40]}.html").parent.mkdir(parents=True, exist_ok=True)
                    (EVIDENCE / "pages" / f"{re.sub(r'[^\\w\\u4e00-\\u9fa5-]', '_', title)}__{re.sub(r'[^\\w\\u4e00-\\u9fa5-]', '_', ch.get('title',''))[:40]}.html").write_text(pr.text[:200000], encoding="utf-8", errors="replace")
                except Exception as exc:
                    page["error"] = str(exc)[:200]
            mod["pages"].append(page)
            print(f"[page] {title}/{ch.get('title','')} {href} apis={len(page.get('apis',[]))}", flush=True)
        modules.append(mod)

    (EVIDENCE / "admin-modules.json").write_text(
        json.dumps({"user": USER, "modules": modules}, ensure_ascii=False, indent=2), encoding="utf-8")
    set_state(step="done", modules=len(modules))
    print("[done] modules:", len(modules), "evidence saved", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
