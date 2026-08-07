"""Batch 117（C116-3）— 覆盖缺口报告测试。"""
from __future__ import annotations

from app.services.coverage_report import build_coverage_report, parse_extraction


def _extraction():
    return {
        "modules": [
            {"name": "首页", "function_points": [{"name": "热门赛事"}, {"name": "搜索入口"}]},
            {"name": "资讯", "function_points": [{"name": "资讯列表"}]},
        ]
    }


def test_full_coverage() -> None:
    generated = {"functional_cases": [
        {"module": "首页", "title": "首页-热门赛事渲染"},
        {"module": "首页", "title": "首页-搜索入口可达"},
        {"module": "资讯", "title": "资讯-资讯列表渲染"},
    ]}
    r = build_coverage_report(_extraction(), generated)
    assert r["gap_count"] == 0
    assert r["total_fp"] == 3 and r["coverage_rate"] == 1.0


def test_gaps_reported() -> None:
    generated = {"functional_cases": [
        {"module": "首页", "title": "首页-热门赛事渲染"},
    ]}
    r = build_coverage_report(_extraction(), generated)
    assert r["gap_count"] == 2
    gap_fps = {g["function_point"] for g in r["gaps"]}
    assert gap_fps == {"搜索入口", "资讯列表"}


def test_empty_extraction() -> None:
    r = build_coverage_report(None, {"functional_cases": []})
    assert r["total_fp"] == 0 and r["gap_count"] == 0 and r["coverage_rate"] == 0.0


def test_parse_extraction() -> None:
    assert parse_extraction('{"modules": []}') == {"modules": []}
    assert parse_extraction("") is None
    assert parse_extraction("not json") is None