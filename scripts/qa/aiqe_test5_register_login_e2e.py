"""TC-AIQE-004 scoped product evidence: REGISTER/Login email vs phone methods.

User clarified the REGISTER entry opens the Register modal and both Register and
Login modes distinguish EMAIL vs PHONE NUMBER. This script verifies that
distinction on test5. The original overlay/cross-feature interference part is
still NOT_TESTED, so the TC remains PARTIAL.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

URL = (
    "https://camelive-g3-test5.elelive.cn/football/"
    "match-singapore-u17-vs-palestine-u17/live/l7oqdehg7gkgr51"
)


def _inputs(page) -> list[dict]:
    return [
        {
            "name": item.get_attribute("name"),
            "placeholder": item.get_attribute("placeholder"),
            "type": item.get_attribute("type"),
        }
        for item in page.locator("input").all()
    ]


def run(out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        page.get_by_text("REGISTER", exact=False).first.click()
        page.wait_for_selector("input[name='email'], input[name='mobile']", timeout=15000)
        page.wait_for_timeout(500)
        if not page.locator("input[name='email']").count():
            page.get_by_text("EMAIL", exact=False).first.click()
            page.wait_for_timeout(500)
        register_email = _inputs(page)
        page.get_by_text("PHONE NUMBER", exact=False).first.click()
        page.wait_for_timeout(600)
        register_phone = _inputs(page)
        page.screenshot(path=str(out / "register_phone.png"))
        page.get_by_text("EMAIL", exact=False).first.click()
        page.wait_for_timeout(400)
        page.get_by_text("Log in", exact=False).first.click()
        page.wait_for_selector("input[name='email'], input[name='mobile']", timeout=15000)
        page.wait_for_timeout(500)
        if not page.locator("input[name='email']").count():
            page.get_by_text("EMAIL", exact=False).first.click()
            page.wait_for_timeout(500)
        login_email = _inputs(page)
        page.screenshot(path=str(out / "login_email.png"))
        page.get_by_text("PHONE NUMBER", exact=False).first.click()
        page.wait_for_timeout(600)
        login_phone = _inputs(page)
        page.screenshot(path=str(out / "login_phone.png"))
        browser.close()

    def has(inputs: list[dict], name: str) -> bool:
        return any(item.get("name") == name for item in inputs)

    checks = {
        "register_email_has_email": has(register_email, "email"),
        "register_email_no_mobile": not has(register_email, "mobile"),
        "register_phone_has_mobile": has(register_phone, "mobile"),
        "register_phone_no_email": not has(register_phone, "email"),
        "login_email_has_email": has(login_email, "email"),
        "login_email_no_mobile": not has(login_email, "mobile"),
        "login_phone_has_mobile": has(login_phone, "mobile"),
        "login_phone_no_email": not has(login_phone, "email"),
    }
    report = {
        "schema_version": "1.0",
        "executed_at": datetime.now(UTC).isoformat(),
        "url": URL,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "tc_status": "PARTIAL",
        "scope": "REGISTER/Login EMAIL vs PHONE NUMBER distinction",
        "overlay_cross_feature": "NOT_TESTED",
        "checks": checks,
        "register_email_inputs": register_email,
        "register_phone_inputs": register_phone,
        "login_email_inputs": login_email,
        "login_phone_inputs": login_phone,
        "screenshots": ["register_phone.png", "login_email.png", "login_phone.png"],
        "gap": "原始 TC-004 的浮层交叉干扰/Defect Draft 未执行；本次仅验证登录方式区分。",
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-login-methods")
    args = parser.parse_args(argv)
    report = run(Path(args.out))
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
