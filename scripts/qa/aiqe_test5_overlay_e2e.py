"""TC-AIQE-004 产品级浮层交叉干扰（test5 直播入口）。

Core profile：直接点击 Login CTA → 登录弹层出现（PASS）。
Integration profile：注入全屏浮层覆盖 Login CTA → 点击被拦截（预期 FAIL），
分类为 CROSS_FEATURE_DEFECT，不归因赛事服务代码。

边界：本脚本验证产品行为与分类，未接入 AIQE Core/Integration 两个正式 Run，
也未创建 Defect Draft，因此 TC-004 只能记 PARTIAL，不能记 VERIFIED。
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

LIVE_URL = "https://camelive-g3-test5.elelive.cn/football/match-singapore-u17-vs-palestine-u17/live/l7oqdehg7gkgr51"


def _close_guide(page) -> None:
    close = page.get_by_role("button", name="Close")
    if close.count():
        try:
            close.first.click(timeout=3000)
            page.wait_for_timeout(800)
        except Exception:
            pass


def run(out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"schema_version": "1.0", "target": LIVE_URL, "profiles": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            # Core profile
            page.goto(LIVE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            _close_guide(page)
            login = page.get_by_text("Login", exact=True).first
            box = login.bounding_box()
            login.click(timeout=5000)
            page.wait_for_timeout(1500)
            inputs = page.locator("input").count()
            page.screenshot(path=str(out / "core_login_modal.png"), full_page=True)
            report["profiles"]["core"] = {
                "status": "PASS" if inputs > 0 else "FAIL",
                "login_box": box,
                "input_count": inputs,
            }
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

            # Integration profile: overlay covers the CTA
            page.goto(LIVE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)
            _close_guide(page)
            page.evaluate(
                """() => {
                  const el = document.createElement('div');
                  el.id = 'aiqe-cross-feature-overlay';
                  el.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:rgba(255,0,0,0.25)';
                  el.setAttribute('data-aiqe-fixture', 'ad-overlay');
                  document.body.appendChild(el);
                }"""
            )
            login = page.get_by_text("Login", exact=True).first
            box = login.bounding_box() or {"x": 0, "y": 0, "width": 1, "height": 1}
            hit = page.evaluate(
                """(pt) => {
                  const el = document.elementFromPoint(pt.x, pt.y);
                  return el ? {id: el.id, cls: el.className, tag: el.tagName} : null;
                }""",
                {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2},
            )
            blocked = False
            try:
                login.click(timeout=2000)
            except Exception:
                blocked = True
            page.screenshot(path=str(out / "integration_overlay.png"), full_page=True)
            report["profiles"]["integration"] = {
                "status": "FAIL" if blocked else "PASS",
                "blocked": blocked,
                "hit_target": hit,
                "classification": "CROSS_FEATURE_DEFECT",
            }
        finally:
            browser.close()
    core = report["profiles"].get("core", {})
    integration = report["profiles"].get("integration", {})
    report["status"] = (
        "PASS"
        if core.get("status") == "PASS"
        and integration.get("status") == "FAIL"
        and integration.get("blocked") is True
        else "FAIL"
    )
    report["executed_at"] = datetime.now(UTC).isoformat()
    report["defect_draft"] = None
    report["gaps"] = ["未接入 AIQE Core/Integration 正式 Run", "未创建 Defect Draft"]
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-overlay")
    args = parser.parse_args(argv)
    report = run(Path(args.out))
    print(json.dumps({"status": report["status"], "profiles": report["profiles"]}, ensure_ascii=False)[:1000])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
