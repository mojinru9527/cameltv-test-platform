"""蓝湖页面树发现测试 —— URL 解析与页面规范化（纯函数，确定性）。"""
from __future__ import annotations


def test_parse_lanhu_url_ids():
    from app.services.lanhu_evidence.page_discovery import parse_lanhu_url

    parsed = parse_lanhu_url(
        "https://lanhuapp.com/web/#/item/project/product?"
        "tid=6324825d-1614-4d73-bc4c-f05cdf0734c1"
        "&pid=cc8cfbd5-16d2-481f-828e-7eb424a91694"
        "&versionId=26af2885-b229-4971-881c-c9bda43492fd"
        "&docId=e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
        "&pageId=2b4c4235b036420787d3e856b5d133d7"
    )

    assert parsed.doc_id == "e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    assert parsed.version_id == "26af2885-b229-4971-881c-c9bda43492fd"
    assert parsed.page_id == "2b4c4235b036420787d3e856b5d133d7"
    assert parsed.project_id == "cc8cfbd5-16d2-481f-828e-7eb424a91694"
    assert parsed.team_id == "6324825d-1614-4d73-bc4c-f05cdf0734c1"


def test_normalize_page_tree_preserves_order_and_path():
    from app.services.lanhu_evidence.page_discovery import normalize_pages

    pages = normalize_pages([
        {"id": "p1", "name": "更新日志", "path": "更新日志"},
        {"id": "p2", "name": "比赛推送", "path": "App/赛事/比赛推送"},
    ])

    assert pages[0].order_index == 0
    assert pages[0].folder == ""
    assert pages[1].page_id == "p2"
    assert pages[1].folder == "App/赛事"
    assert pages[1].order_index == 1
