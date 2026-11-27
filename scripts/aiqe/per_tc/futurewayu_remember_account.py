"""TC-AIQE-008：WWY-V5-006 记住账号修复回归（点击回归）。

步骤：登录页输入账号 → 勾选“记住账号” → 登录/返回登录页 → 刷新 → 账号应回填。
退出码 0=PASS，1=FAIL。
"""
from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/aiqe/v1.6/evidence/product/TC-AIQE-008"
USERNAME = "tester-operator"


def _captcha() -> str:
    with urllib.request.urlopen("http://127.0.0.1:18081/captcha", timeout=10) as response:
        return json.loads(response.read().decode())["code"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://xinyuwadao.com/login", wait_until="domcontentloaded", timeout=45000)
        page.locator('input[placeholder="用户名"]').fill(USERNAME)
        page.locator('input[placeholder="密码"]').fill("123456")
        page.locator('input[placeholder="验证码"]').fill(_captcha())
        page.get_by_text("记住账号").click()
        page.get_by_role("button", name="登录").click(force=True)
        page.wait_for_timeout(3000)
        page.goto("https://xinyuwadao.com/login", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(1000)
        value = page.locator('input[placeholder="用户名"]').input_value()
        remember = page.evaluate("localStorage.getItem('rememberMe')")
        stored_user = page.evaluate("localStorage.getItem('username')")
        page.screenshot(path=str(OUT / "remember-account.png"), full_page=False)
        browser.close()
    passed = value == USERNAME and str(remember).lower() == "true" and stored_user == USERNAME
    result = {
        "schema_version": "1.0",
        "tc_id": "TC-AIQE-008",
        "defect_id": "WWY-V5-006",
        "case_id": "TC-ADM-01-D",
        "status": "PASS" if passed else "FAIL",
        "generated_at": datetime.now(UTC).isoformat(),
        "before": "输入框空、localStorage 无记忆项",
        "expected": "登录页刷新后账号自动回填，localStorage 保留 username/rememberMe",
        "actual": {"username_value": value, "rememberMe": remember, "stored_username": stored_user},
        "screenshot": str((OUT / "remember-account.png").relative_to(ROOT)),
        "conclusion": "修复回归通过：账号回填且 localStorage 持久化。" if passed else "修复未生效。",
    }
    (OUT / "remember-account.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "actual": result["actual"]}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
