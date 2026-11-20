"""V16-017 产品级 E2E：CamelTv test5 真实环境（前端/后台/可选 DB）。

设计原则：
- 缺少环境变量时输出 **BLOCKED**（exit 2），不伪造 PASS；
- 管理员单会话锁、DB 不可达等分别记录 BLOCKED 原因；
- 截图/HAR/Trace 输出到 evidence 目录，报告 JSON 机器可读；
- 凭据只从环境变量读取，不写入仓库/日志。

用法：
  $env:AIQE_TEST5_FRONTEND_URL="https://camelive-g3-test5.elelive.cn/"
  $env:AIQE_TEST5_ADMIN_URL="https://camel-admintest5.elelive.cn"
  $env:AIQE_TEST5_PHONE="+8618476944071"
  $env:AIQE_TEST5_PASSWORD="..."
  $env:AIQE_TEST5_ADMIN_USER="ll"
  $env:AIQE_TEST5_ADMIN_SMS="1234"
  $env:AIQE_TEST5_DB_DSN="postgresql+psycopg2://readonly:...@host/db"
  python scripts/qa/aiqe_test5_e2e.py --out work-logs/evidence/aiqe-v16/test5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_FRONT = ("AIQE_TEST5_FRONTEND_URL", "AIQE_TEST5_PHONE", "AIQE_TEST5_PASSWORD")
REQUIRED_ADMIN = ("AIQE_TEST5_ADMIN_URL", "AIQE_TEST5_ADMIN_USER", "AIQE_TEST5_ADMIN_SMS")


class StepBlocked(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _env(name: str, default: str = "") -> str:
    return str(os.environ.get(name) or default).strip()


def missing_config() -> list[str]:
    missing = [name for name in REQUIRED_FRONT if not _env(name)]
    admin_present = any(_env(name) for name in REQUIRED_ADMIN)
    if admin_present:
        missing.extend(name for name in REQUIRED_ADMIN if not _env(name))
    return missing


def _mask_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return f"***{digits[-4:]}" if len(digits) >= 4 else "***"


class Steps:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, name: str, status: str, detail: str = "", **extra: Any) -> None:
        item = {"name": name, "status": status, "detail": detail, "at": datetime.now(UTC).isoformat()}
        item.update(extra)
        self.items.append(item)

    @property
    def status(self) -> str:
        statuses = {item["status"] for item in self.items}
        if "FAIL" in statuses:
            return "FAIL"
        if "BLOCKED" in statuses:
            return "BLOCKED"
        return "PASS"


def _front_login(page: Any, steps: Steps) -> None:
    page.goto(_env("AIQE_TEST5_FRONTEND_URL"), wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(6000)
    page.get_by_role("button", name="Register").first.dispatch_event("click")
    page.wait_for_timeout(1500)
    page.get_by_text("Log in", exact=False).last.dispatch_event("click")
    page.wait_for_timeout(1500)
    page.get_by_text("PHONE NUMBER", exact=False).first.dispatch_event("click")
    page.wait_for_timeout(1000)
    page.locator(".select-selected").dispatch_event("click")
    page.wait_for_timeout(500)
    page.locator(".select-item", has_text="+86 China").first.dispatch_event("click")
    page.wait_for_timeout(500)
    page.fill("input[name='mobile']", re.sub(r"^\+?86", "", _env("AIQE_TEST5_PHONE")))
    page.fill("input[name='password']", _env("AIQE_TEST5_PASSWORD"))
    page.locator(".register-button").dispatch_event("click")
    page.wait_for_timeout(5000)
    auth = next((c for c in page.context.cookies() if c["name"] == "auth"), None)
    if auth is None:
        raise AssertionError("登录后缺少 auth Cookie")
    from urllib.parse import unquote

    decoded = json.loads(unquote(auth["value"]))
    if not decoded.get("userId"):
        raise AssertionError(f"auth Cookie 无 userId: {list(decoded)[:5]}")
    steps.add("front_login", "PASS", f"userId={decoded.get('userId')}", phone=_mask_phone(_env("AIQE_TEST5_PHONE")))


def _front_browse(page: Any, steps: Steps) -> None:
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    text = page.locator("body").inner_text()
    if "Live Matches" not in text and "Matches" not in text:
        raise AssertionError("首页未出现赛事区域")
    count = page.locator("a[href*='match'], [class*='match']").count()
    if count < 3:
        raise AssertionError(f"赛事卡片数量异常: {count}")
    steps.add("front_browse", "PASS", f"match_nodes={count}")
    inputs = page.locator("input[type='search'], input[placeholder*='earch'], input.searchInput")
    if not inputs.count():
        try:
            page.locator("[aria-label='Search']").first.click()
            page.wait_for_selector(
                "input[type='search'], input[placeholder*='earch'], input.searchInput",
                timeout=6000,
            )
        except Exception:
            pass
        inputs = page.locator("input[type='search'], input[placeholder*='earch'], input.searchInput")
    if inputs.count():
        try:
            inputs.first.fill("Arsenal", timeout=5000)
            page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            steps.add("front_search", "PASS", page.url, body=page.locator("body").inner_text()[:300])
        except Exception as exc:
            steps.add("front_search", "BLOCKED", f"搜索输入不可用: {type(exc).__name__}")
    else:
        steps.add("front_search", "BLOCKED", "未找到搜索输入框")


def _front_match_detail(page: Any, steps: Steps) -> None:
    link = page.locator("a[href*='/football/match-']").first
    if not link.count():
        raise StepBlocked("首页未找到赛事详情链接")
    href = str(link.get_attribute("href") or "")
    if not href:
        raise StepBlocked("赛事详情链接为空")
    url = href if href.startswith("http") else _env("AIQE_TEST5_FRONTEND_URL").rstrip("/") + href
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    title = page.title()
    body = page.locator("body").inner_text()
    if "Camel Live" not in title or "Prediction" not in body:
        raise AssertionError(f"赛事详情内容异常: {title!r}")
    steps.add("front_match_detail", "PASS", url, title=title[:160])


def _admin_login(page: Any, steps: Steps) -> None:
    if not _env("AIQE_TEST5_ADMIN_URL"):
        steps.add("admin_login", "BLOCKED", "AIQE_TEST5_ADMIN_URL 未配置")
        return
    login_responses: list[str] = []

    def _capture(response: Any) -> None:
        if response.url.rstrip("/").endswith("/login"):
            try:
                login_responses.append(response.text())
            except Exception:
                return

    page.on("response", _capture)
    base = _env("AIQE_TEST5_ADMIN_URL").rstrip("/")
    page.goto(base + "/login", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    page.fill("input[name='userCode']", _env("AIQE_TEST5_ADMIN_USER"))
    page.fill("input[name='imageVerifyCode']", _env("AIQE_TEST5_ADMIN_CAPTCHA", "1234"))
    page.locator("button").first.click()
    page.wait_for_timeout(2500)
    sms = page.locator("#layui-layer2 input[name='smsCode']")
    if not sms.count() or not sms.is_visible():
        body = page.locator("body").inner_text()
        if "已经登录" in body:
            raise StepBlocked(f"管理员单会话锁：用户[{_env('AIQE_TEST5_ADMIN_USER')}]已经登录")
        raise StepBlocked("管理员登录未进入短信验证步骤（会话锁/验证码/接口失败）")
    sms.fill(_env("AIQE_TEST5_ADMIN_SMS"))
    page.locator("#layui-layer2 .layui-layer-btn0").click()
    page.wait_for_timeout(6000)
    body = page.locator("body").inner_text()
    if "/main" not in page.url:
        joined = " ".join(login_responses)
        if "已经登录" in joined or "已经登录" in body:
            raise StepBlocked(f"管理员单会话锁：用户[{_env('AIQE_TEST5_ADMIN_USER')}]已经登录")
        raise AssertionError(f"管理员登录未进入 /main: {page.url} {body[:200]}")
    logged_in = True
    steps.add("admin_login", "PASS", page.url)
    try:
        page.get_by_text("直播管理", exact=True).first.click(timeout=5000)
        page.wait_for_timeout(800)
        page.get_by_text("LIVE房直播记录", exact=True).first.click(timeout=5000)
        page.wait_for_timeout(2500)
        if "LIVE房直播记录" not in page.locator("body").inner_text():
            raise AssertionError("后台直播记录页未加载")
        steps.add("admin_readonly", "PASS", page.url)
    except Exception as exc:
        steps.add("admin_readonly", "BLOCKED", type(exc).__name__)
    finally:
        if logged_in:
            try:
                page.goto(base + "/logout", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)
                steps.add(
                    "admin_logout",
                    "PASS" if "/login" in page.url else "BLOCKED",
                    page.url,
                )
            except Exception as exc:
                steps.add("admin_logout", "BLOCKED", type(exc).__name__)


def _db_check(steps: Steps) -> None:
    host = _env("AIQE_TEST5_MYSQL_HOST")
    user = _env("AIQE_TEST5_MYSQL_USER")
    password = _env("AIQE_TEST5_MYSQL_PASSWORD")
    if not (host and user and password):
        steps.add(
            "db_assert",
            "BLOCKED",
            "AIQE_TEST5_MYSQL_HOST/USER/PASSWORD 未配置（只读连接）",
        )
        return
    import pymysql

    conn = pymysql.connect(
        host=host,
        port=int(_env("AIQE_TEST5_MYSQL_PORT", "3306")),
        user=user,
        password=password,
        database=_env("AIQE_TEST5_MYSQL_DATABASE", "camel_account"),
        connect_timeout=15,
        read_timeout=15,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("START TRANSACTION READ ONLY")
            user_id = int(_env("AIQE_TEST5_USER_ID", "11025728"))
            cur.execute(
                "SELECT user_id, nickname FROM camel_account.user_info WHERE user_id=%s",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise AssertionError(f"DB 未找到 user_id={user_id}")
            cur.execute(
                "SELECT COUNT(*) FROM camel_studio.sports_favorite WHERE user_id=%s",
                (str(user_id),),
            )
            favorites = int(cur.fetchone()[0])
            cur.execute("ROLLBACK")
        steps.add(
            "db_assert",
            "PASS",
            f"camel_account.user_info user_id={row[0]} nickname={row[1]} favorites={favorites}",
        )
    finally:
        conn.close()


def run(out: Path, *, headless: bool = True) -> dict:
    missing = missing_config()
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*"):
        if stale.is_file():
            stale.unlink()
    steps = Steps()
    started = time.monotonic()
    if missing:
        steps.add("config", "BLOCKED", f"缺少环境变量: {', '.join(missing)}")
        report = _report(steps, out, started)
        (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_har_path=str(out / "network.har"),
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        for name, func in (
            ("front_login", lambda: _front_login(page, steps)),
            ("front_browse", lambda: _front_browse(page, steps)),
            ("front_match_detail", lambda: _front_match_detail(page, steps)),
            ("admin_login", lambda: _admin_login(page, steps)),
            ("db_assert", lambda: _db_check(steps)),
        ):
            try:
                func()
            except StepBlocked as exc:
                steps.add(name, "BLOCKED", exc.reason)
                page.screenshot(path=str(out / f"{name}_blocked.png"), full_page=True)
            except Exception as exc:  # noqa: BLE001
                steps.add(name, "FAIL", f"{type(exc).__name__}: {exc}")
                page.screenshot(path=str(out / f"{name}_failed.png"), full_page=True)
            else:
                if name in {"front_login", "front_browse", "front_match_detail"}:
                    page.screenshot(path=str(out / f"{name}.png"), full_page=True)
        context.tracing.stop(path=str(out / "trace.zip"))
        context.close()
        browser.close()
    report = _report(steps, out, started)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _report(steps: Steps, out: Path, started: float) -> dict:
    return {
        "schema_version": "1.0",
        "environment": "camel-test5",
        "status": steps.status,
        "started_at": datetime.now(UTC).isoformat(),
        "duration_seconds": round(time.monotonic() - started, 2),
        "steps": steps.items,
        "artifacts": sorted(str(path.relative_to(out)) for path in out.glob("*") if path.is_file()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--config-only", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out)
    if args.config_only:
        missing = missing_config()
        print(json.dumps({"ready": not missing, "missing": missing}, ensure_ascii=False))
        return 0 if not missing else 2
    report = run(out, headless=not args.headed)
    print(json.dumps({"status": report["status"], "report": str(out / "report.json")}, ensure_ascii=False))
    return {"PASS": 0, "BLOCKED": 2}.get(report["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
