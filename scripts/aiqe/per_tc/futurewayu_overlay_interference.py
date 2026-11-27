"""TC-AIQE-004（适配）：其他功能浮层交叉干扰（未来娃屿后台命令面板）。

广告模块不属于未来娃屿；按 TC 标题的“其他功能浮层”用真实命令面板（Ctrl+K）验证：
1) 浮层打开后，点击底层页面不应触发导航；
2) Esc 关闭浮层后，底层导航恢复可用。
退出码 0=PASS，1=FAIL。
"""
from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/aiqe/v1.6/evidence/product/TC-AIQE-004"


def _captcha() -> str:
    with urllib.request.urlopen("http://127.0.0.1:18081/captcha", timeout=10) as response:
        return json.loads(response.read().decode())["code"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("https://xinyuwadao.com/login", wait_until="domcontentloaded", timeout=45000)
        page.locator('input[placeholder="用户名"]').fill("tester-operator")
        page.locator('input[placeholder="密码"]').fill("123456")
        page.locator('input[placeholder="验证码"]').fill(_captcha())
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
        page.screenshot(path=str(OUT / "overlay-interference.png"), full_page=False)
        browser.close()
    passed = bool(opened and blocked_navigation and closed and navigated)
    result = {
        "schema_version": "1.0",
        "tc_id": "TC-AIQE-004",
        "adaptation": "广告模块不属于未来娃屿；使用后台命令面板作为“其他功能浮层”",
        "status": "PASS" if passed else "FAIL",
        "generated_at": datetime.now(UTC).isoformat(),
        "overlay": {"type": "command_palette", "trigger": "Ctrl+K", "text": palette_text},
        "checks": {
            "opened": opened,
            "blocked_underlying_navigation": blocked_navigation,
            "closed_by_escape": closed,
            "navigation_recovered": navigated,
        },
        "urls": {"home": home_url, "before_click": before_click, "after_click": after_click, "recovery": recovery_url},
        "screenshot": str((OUT / "overlay-interference.png").relative_to(ROOT)),
        "conclusion": "浮层打开时底层导航未被误触，关闭后导航恢复。" if passed else "浮层交叉干扰验证失败。",
    }
    (OUT / "overlay-interference.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "checks": result["checks"], "urls": result["urls"]}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
