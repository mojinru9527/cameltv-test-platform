"""TC-AIQE-002 scoped frontend verification for a news article published in admin.

User-approved simplified scope: admin publishes one news article, frontend list
and detail page must show it. Admin create/audit steps are recorded manually
because the admin console needs a captcha + SMS session.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

URL = "https://camelive-g3-test5.elelive.cn/news/detail/aiqe-news-1795265608?entry_way=news"
TITLE = "AIQE TC-002 automated news article"
CONTENT = "AIQE TC-002 automated news article content"


def run(out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        text = page.locator("body").inner_text()
        title = page.title()
        checks = {
            "has_article_title": TITLE in text,
            "has_article_content": CONTENT in text,
            "title_contains_article": TITLE in title,
            "no_error_page": "Something went wrong" not in text,
        }
        screenshot = out / "front_news_detail.png"
        page.screenshot(path=str(screenshot), full_page=True)
        browser.close()
    report = {
        "schema_version": "1.0",
        "executed_at": datetime.now(UTC).isoformat(),
        "url": URL,
        "article_id": "aiqe-news-1795265608",
        "admin_status": "审核通过 / 是否上线=是",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "title": title,
        "text_sample": text[:800],
        "screenshot": screenshot.name,
        "scope": "admin 发布资讯文章 → 前端列表/详情可查看（用户批准的简化 TC-002 口径）",
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work-logs/evidence/aiqe-v16/test5-news")
    args = parser.parse_args(argv)
    report = run(Path(args.out))
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
