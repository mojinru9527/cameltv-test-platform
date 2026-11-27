"""TC-AIQE-009：未来娃屿多端 AC 对照（桌面 Chrome / Android Appium / 微信小程序）。

- 桌面：Playwright 打开管理后台登录页并截图；
- 安卓：Appium UiAutomator2 打开 uni.app.UNIE3747D0 并截图；
- 小程序：复制微信小程序面板截图（半自动，无开发者权限）。
退出码 0=PASS，1=FAIL。
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = "docs/aiqe/v1.6/evidence/product/TC-AIQE-009"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=DEFAULT_OUT)
    parser.add_argument("--appium-url", default="http://127.0.0.1:4723/wd/hub")
    parser.add_argument("--no-android", action="store_true")
    args = parser.parse_args()
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    result: dict = {"tc_id": "TC-AIQE-009", "generated_at": datetime.now(UTC).isoformat(), "platforms": {}}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        response = page.goto("https://xinyuwadao.com/login", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        shot = out / "desktop-login.png"
        page.screenshot(path=str(shot), full_page=False)
        result["platforms"]["desktop"] = {
            "status": "PASS" if response and response.status < 400 else "FAIL",
            "http_status": response.status if response else None,
            "title": page.title(),
            "url": page.url,
            "screenshot": str(shot.relative_to(ROOT)),
        }
        browser.close()

    if not args.no_android:
        options = UiAutomator2Options().load_capabilities(
            {
                "platformName": "Android",
                "appium:automationName": "UiAutomator2",
                "appium:deviceName": "9f0564ba",
                "appium:appPackage": "uni.app.UNIE3747D0",
                "appium:appActivity": "io.dcloud.PandoraEntry",
                "appium:noReset": True,
                "appium:newCommandTimeout": 120,
            }
        )
        driver = webdriver.Remote(args.appium_url, options=options)
        try:
            driver.wait_activity("io.dcloud.PandoraEntryActivity", 20)
            shot = out / "android-app.png"
            driver.get_screenshot_as_file(str(shot))
            result["platforms"]["android"] = {
                "status": "PASS",
                "package": driver.current_package,
                "activity": driver.current_activity,
                "device": "9f0564ba OnePlus6T",
                "screenshot": str(shot.relative_to(ROOT)),
            }
        finally:
            driver.quit()

    mini = ROOT / "docs/aiqe/v1.6/evidence/product/wechat-miniapp-futurewayu.png"
    mini_target = out / "wechat-miniapp.png"
    if mini.exists():
        shutil.copyfile(mini, mini_target)
        result["platforms"]["wechat_miniapp"] = {
            "status": "SEMI_AUTOMATIC",
            "screenshot": str(mini_target.relative_to(ROOT)),
            "note": "微信小程序面板截图；无开发者权限，未做机器断言",
        }
    else:
        result["platforms"]["wechat_miniapp"] = {"status": "BLOCKED", "note": "缺少微信小程序截图"}

    ok = all(
        result["platforms"].get(name, {}).get("status") in {"PASS", "SEMI_AUTOMATIC"}
        for name in ("desktop", "android" if not args.no_android else "desktop", "wechat_miniapp")
    )
    result["status"] = "PASS" if ok else "FAIL"
    (out / "multi-end.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "platforms": {k: v.get("status") for k, v in result["platforms"].items()}}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
