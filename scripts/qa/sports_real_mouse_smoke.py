"""Real Chrome mouse smoke for a SPA page.

This uses a real browser and mouse events (move/down/up), not locator.click.
It does not bypass WAF; it expects the page to be reachable by a real browser.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--y", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-title", default="Camel Live")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        response = page.goto(args.url, wait_until="domcontentloaded", timeout=45_000)
        time.sleep(3)
        before = {"status": None if response is None else response.status, "url": page.url, "title": page.title()}
        page.screenshot(path=str(out / "before.png"))
        page.mouse.move(args.x, args.y)
        page.mouse.down()
        page.mouse.up()
        time.sleep(4)
        after = {
            "url": page.url,
            "title": page.title(),
            "body": page.locator("body").inner_text()[:1000],
        }
        page.screenshot(path=str(out / "after.png"))
        navigated = after["title"] != before["title"]
        ok = args.expected_title.lower() in after["title"].lower() and navigated
        result = {
            "result": "PASS" if ok else "FAIL",
            "navigated": navigated,
            "before": before,
            "after": after,
            "mouse": {"x": args.x, "y": args.y},
            "expected_title": args.expected_title,
        }
        (out / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps({"result": result["result"], "before": before, "after_title": after["title"]}, ensure_ascii=False))
        browser.close()
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
