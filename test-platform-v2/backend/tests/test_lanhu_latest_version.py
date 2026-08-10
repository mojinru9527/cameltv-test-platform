"""Batch 137 — 证据采集"仅最新版本"过滤测试。"""
from __future__ import annotations

from app.services.external.lanhu_provider import _filter_latest_version_pages


def test_keeps_only_latest_version_folder():
    pages = [
        {"folder": "15.0.0/首页", "path": "15.0.0/首页", "name": "a", "id": "1"},
        {"folder": "15.0.0/赛事", "path": "15.0.0/赛事", "name": "b", "id": "2"},
        {"folder": "16.0.0/首页", "path": "16.0.0/首页", "name": "c", "id": "3"},
        {"folder": "16.0.0/新增", "path": "16.0.0/新增", "name": "d", "id": "4"},
        {"folder": "通用", "path": "通用/说明", "name": "e", "id": "5"},
    ]
    out = _filter_latest_version_pages(pages)
    assert [p["id"] for p in out] == ["3", "4"]


def test_no_version_folders_returns_all():
    pages = [
        {"folder": "首页", "name": "a", "id": "1"},
        {"folder": "赛事", "name": "b", "id": "2"},
    ]
    assert len(_filter_latest_version_pages(pages)) == 2


def test_version_sort_honors_major_minor():
    pages = [
        {"folder": "9.10.0/首页", "name": "a", "id": "1"},
        {"folder": "10.0.0/首页", "name": "b", "id": "2"},
    ]
    out = _filter_latest_version_pages(pages)
    assert [p["id"] for p in out] == ["2"]


def test_empty_returns_empty():
    assert _filter_latest_version_pages([]) == []
