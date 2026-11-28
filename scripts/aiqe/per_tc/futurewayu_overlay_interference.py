"""TC-AIQE-004（适配）：其他功能浮层交叉干扰（未来娃屿后台命令面板）。

广告模块不属于未来娃屿；按 TC 标题的"其他功能浮层"用真实命令面板（Ctrl+K）验证：
1) 浮层打开后，点击底层页面不应触发导航；
2) Esc 关闭浮层后，底层导航恢复可用。

V1.6.2 FIX-007/FIX-009：
- 状态只用 ``scripts/aiqe/statuses.py`` 的 PASS/FAIL/BLOCKED，不再自定义折算；
- 账号/密码只从 CI Secret 读取（``FUTUREWAYU_TEST_USERNAME`` / ``FUTUREWAYU_TEST_PASSWORD``），
  缺失即 BLOCKED，禁止默认值回退；输出只记录 Secret 名称；
- 退出码 0 仅当 PASS。

用法
----
    python scripts/aiqe/per_tc/futurewayu_overlay_interference.py \\
      --out-dir docs/aiqe/v1.6/evidence/product/TC-AIQE-004
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AIQE_DIR = SCRIPT_DIR.parent
if str(AIQE_DIR) not in sys.path:
    sys.path.insert(0, str(AIQE_DIR))

from statuses import BLOCKED, FAIL, PASS, is_pass  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = "docs/aiqe/v1.6/evidence/product/TC-AIQE-004"
DEFAULT_BASE_URL = "https://xinyuwadao.com"

SECRET_ENV = {
    "username": "FUTUREWAYU_TEST_USERNAME",
    "password": "FUTUREWAYU_TEST_PASSWORD",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def resolve_credentials(environ: dict | None = None) -> dict:
    """只从环境变量解析测试账号；缺失即返回空值列表，绝不回退默认值。"""
    env = os.environ if environ is None else environ
    username = str(env.get(SECRET_ENV["username"]) or "").strip()
    password = str(env.get(SECRET_ENV["password"]) or "").strip()
    missing = [
        name for name, value in zip(SECRET_ENV.values(), (username, password)) if not value
    ]
    return {
        "username": username,
        "password": password,
        "available": not missing,
        "missing": missing,
        "secret_names": list(SECRET_ENV.values()),
    }


def evaluate_overlay(checks: object, *, blocked_reason: str = "") -> str:
    """纯函数：四项业务检查全部为 True 才 PASS，否则 FAIL；缺环境为 BLOCKED。"""
    if blocked_reason:
        return BLOCKED
    values = checks if isinstance(checks, dict) else {}
    required = ("opened", "blocked_underlying_navigation", "closed_by_escape", "navigation_recovered")
    if all(values.get(name) is True for name in required):
        return PASS
    return FAIL


def _captcha(captcha_url: str, timeout: float = 10.0) -> str:
    with urllib.request.urlopen(captcha_url, timeout=timeout) as response:  # noqa: S310
        return str(json.loads(response.read().decode())["code"])


def _artifact_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _safe_error(exc: BaseException, secrets: list[str]) -> str:
    """异常信息先脱敏：任何 Secret 取值都替换为 ***。"""
    text = f"{type(exc).__name__}: {str(exc)[:300]}"
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def _observe(args: argparse.Namespace, creds: dict, out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    base = args.base_url.rstrip("/")
    shot = out / "overlay-interference.png"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"{base}/login", wait_until="domcontentloaded", timeout=45000)
            page.locator('input[placeholder="用户名"]').fill(creds["username"])
            page.locator('input[placeholder="密码"]').fill(creds["password"])
            captcha = _captcha(args.captcha_url) if args.captcha_url else ""
            if captcha:
                page.locator('input[placeholder="验证码"]').fill(captcha)
            page.get_by_role("button", name="登录").click(force=True)
            page.wait_for_timeout(3000)
            home_url = page.url
            page.keyboard.press("Control+k")
            page.wait_for_timeout(800)
            dialog = page.locator("[role=dialog]")
            opened = dialog.count() > 0 and dialog.first.is_visible()
            palette_text = dialog.first.inner_text()[:200] if opened else ""
            before_click = page.url
            page.mouse.click(30, 420)  # 底层侧边栏区域；浮层应拦截
            page.wait_for_timeout(500)
            after_click = page.url
            blocked_navigation = after_click == before_click
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            closed = dialog.count() == 0 or not dialog.first.is_visible()
            page.get_by_text("轮播图", exact=True).first.click()
            page.wait_for_timeout(2000)
            recovery_url = page.url
            navigated = "banner" in recovery_url or recovery_url != home_url
            page.screenshot(path=str(shot), full_page=False)
        finally:
            browser.close()
    return {
        "checks": {
            "opened": bool(opened),
            "blocked_underlying_navigation": bool(blocked_navigation),
            "closed_by_escape": bool(closed),
            "navigation_recovered": bool(navigated),
        },
        "overlay": {"type": "command_palette", "trigger": "Ctrl+K", "text": palette_text},
        "urls": {
            "home": home_url,
            "before_click": before_click,
            "after_click": after_click,
            "recovery": recovery_url,
        },
        "artifact": _artifact_ref(shot),
        "identity": {"executed_as": f"secret:{SECRET_ENV['username']}"},
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TC-AIQE-004 浮层交叉干扰")
    parser.add_argument("--out-dir", default=DEFAULT_OUT)
    parser.add_argument(
        "--base-url", default=os.environ.get("FUTUREWAYU_BASE_URL", DEFAULT_BASE_URL)
    )
    parser.add_argument("--captcha-url", default=os.environ.get("FUTUREWAYU_CAPTCHA_URL", ""))
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    args = build_parser().parse_args(argv)
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    creds = resolve_credentials()
    blocked_reason = ""
    observation: dict = {}
    if not creds["available"]:
        blocked_reason = "缺少 Secret: " + ", ".join(creds["missing"]) + "（禁止默认值回退）"
    else:
        try:
            observation = _observe(args, creds, out)
        except Exception as exc:  # noqa: BLE001 - 执行失败必须降级为 BLOCKED
            blocked_reason = _safe_error(exc, [creds["username"], creds["password"]])

    checks = observation.get("checks", {})
    status = evaluate_overlay(checks, blocked_reason=blocked_reason)
    result = {
        "schema_version": "2.0",
        "artifact_kind": "overlay-interference",
        "tc_id": "TC-AIQE-004",
        "adaptation": "广告模块不属于未来娃屿；使用后台命令面板作为“其他功能浮层”",
        "status": status,
        "generated_at": _now(),
        "base_url": args.base_url,
        "overlay": observation.get("overlay", {}),
        "checks": checks,
        "urls": observation.get("urls", {}),
        "screenshot": observation.get("artifact", ""),
        "identity": observation.get("identity", {}),
        "credential_secret_names": list(SECRET_ENV.values()),
        "credential_available": creds["available"],
        "blocked_reason": blocked_reason,
        "conclusion": (
            "浮层打开时底层导航未被误触，关闭后导航恢复。"
            if status == PASS
            else blocked_reason or "浮层交叉干扰验证失败。"
        ),
    }
    (out / "overlay-interference.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": status,
                "checks": checks,
                "blocked_reason": blocked_reason,
            },
            ensure_ascii=False,
        )
    )
    return 0 if is_pass(status) else 1


if __name__ == "__main__":
    raise SystemExit(main())
