"""TC-AIQE-009: PC Chromium + Android Quark multi-end AC evidence.

Android Chrome is unavailable on the test device; the user explicitly approved
Quark as the Android browser for this run. The report records that deviation.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

URL = (
    "https://camelive-g3-test5.elelive.cn/football/"
    "match-singapore-u17-vs-palestine-u17/live/l7oqdehg7gkgr51"
)
ADB = r"C:\Users\26029\AppData\Local\Android\Sdk\platform-tools\adb.exe"


def _adb(*args: str, timeout: int = 60) -> str:
    result = subprocess.run([ADB, *args], capture_output=True, text=True, timeout=timeout)
    return (result.stdout or "") + (result.stderr or "")


def run(out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"schema_version": "1.0", "url": URL, "executed_at": datetime.now(UTC).isoformat()}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        pc_title = page.title()
        page.screenshot(path=str(out / "pc_chromium.png"))
        browser.close()
    report["pc"] = {
        "browser": "Chromium (Playwright)",
        "title": pc_title,
        "status": "PASS" if "Singapore U17" in pc_title and "Camel Live" in pc_title else "FAIL",
        "screenshot": "pc_chromium.png",
    }

    _adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", URL)
    time.sleep(10)
    focus = _adb("shell", "dumpsys", "window")
    package = "com.quark.browser" if "com.quark.browser" in focus else ""
    _adb("shell", "uiautomator", "dump", "/sdcard/aiqe_tc009.xml")
    _adb("pull", "/sdcard/aiqe_tc009.xml", str(out / "android_ui.xml"))
    _adb("shell", "screencap", "-p", "/sdcard/aiqe_tc009.png")
    _adb("pull", "/sdcard/aiqe_tc009.png", str(out / "android_quark.png"))
    xml = (out / "android_ui.xml").read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r'text="([^"]*Camel Live[^"]*)"', xml)
    android_title = matches[0] if matches else ""
    report["android"] = {
        "device": _adb("shell", "getprop", "ro.product.model").strip(),
        "os": _adb("shell", "getprop", "ro.build.version.release").strip(),
        "browser_package": package,
        "browser": "Quark",
        "title": android_title,
        "status": "PASS" if "Singapore U17" in android_title and "Camel Live" in android_title else "FAIL",
        "screenshot": "android_quark.png",
        "deviation": "Android Chrome unavailable; user approved Quark for this run; VERIFIED is scope-approved, not Chrome-verified",
    }
    report["status"] = "PASS" if report["pc"]["status"] == "PASS" and report["android"]["status"] == "PASS" else "FAIL"
    report["tc_status"] = "VERIFIED" if report["status"] == "PASS" else "BLOCKED"
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-multidevice")
    args = parser.parse_args(argv)
    report = run(Path(args.out))
    print(json.dumps({"status": report["status"], "pc": report["pc"]["status"], "android": report["android"]["status"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
