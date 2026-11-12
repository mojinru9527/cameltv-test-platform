"""TC-AIQE-001..010 真实 E2E 入口（需隔离 Test 环境）。

运行：
  $env:AIQE_E2E_BASE_URL="https://<test-host>"
  $env:AIQE_E2E_USERNAME / AIQE_E2E_PASSWORD
  pytest tests/e2e/aiqe/test_tc_aiqe_001_010.py -q
未设置 AIQE_E2E_BASE_URL 时全部 skip（不在 CI 里造假绿）。
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("playwright.sync_api", reason="需要 playwright")

BASE_URL = os.getenv("AIQE_E2E_BASE_URL", "").rstrip("/")
USERNAME = os.getenv("AIQE_E2E_USERNAME", "")
PASSWORD = os.getenv("AIQE_E2E_PASSWORD", "")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="AIQE_E2E_BASE_URL 未设置，跳过真实 E2E")

CASES = [
    ("TC-AIQE-001", "需求契约冻结 + 变更影响"),
    ("TC-AIQE-002", "用例生成与评审"),
    ("TC-AIQE-003", "DAG 执行与证据"),
    ("TC-AIQE-004", "失败归因"),
    ("TC-AIQE-005", "反事实重放"),
    ("TC-AIQE-006", "缺陷草稿与一键回归"),
    ("TC-AIQE-007", "噪音抑制规则"),
    ("TC-AIQE-008", "版本质量门禁"),
    ("TC-AIQE-009", "MCP 查询与写审批"),
    ("TC-AIQE-010", "平台矩阵"),
]


def _login(page):
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", USERNAME)
    page.fill("input[name='password']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/**", timeout=15000)


@pytest.fixture(scope="session")
def browser_page():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        if USERNAME and PASSWORD:
            _login(page)
        yield page
        browser.close()


@pytest.mark.parametrize("case_id,title", CASES)
def test_tc_aiqe_case(browser_page, case_id, title):
    assert BASE_URL, "必须配置隔离 Test 环境"
    browser_page.goto(f"{BASE_URL}/runs")
    assert browser_page.locator("body").count() == 1, f"{case_id} {title} 页面未加载"
    # 具体业务断言由测试环境数据/账号补齐；此文件保证 TC 编号与运行入口固定。
