"""M6 / TA-034.2：Asset-map 接入单测。"""
from __future__ import annotations

import pytest

from app.aiqe.services.asset_map_integration import (
    RULE_IDS,
    AssetMapError,
    build_evidence_bundle,
    build_page_map,
    coverage_metrics,
    group_rule_results,
)

PAGES = [
    {"path": "/home", "title": "首页", "links": ["/live"]},
    {"path": "/live", "title": "直播", "links": ["/match"]},
    {"path": "/match", "title": "赛事", "links": []},
]

RESULTS = [
    {"rule_id": "A01", "status": "PASS", "page": "/home"},
    {"rule_id": "A01", "status": "FAIL", "page": "/live"},
    {"rule_id": "A02", "status": "PASS", "page": "/live"},
    {"rule_id": "A03", "status": "PASS", "page": "/match"},
]


def test_page_map_nodes_and_edges():
    page_map = build_page_map(PAGES)
    assert [node["id"] for node in page_map["nodes"]] == ["/home", "/live", "/match"]
    assert {"from": "/home", "to": "/live"} in page_map["edges"]
    assert len(page_map["edges"]) == 2


def test_rule_grouping_has_24_rules():
    summary = group_rule_results(RESULTS)
    assert len(summary["rules"]) == 24
    assert summary["rules"]["A01"] == {"total": 2, "passed": 1, "failed": 1}
    assert summary["covered_rules"] == 3
    assert summary["unknown_rules"] == []


def test_unknown_rule_flagged():
    summary = group_rule_results([{"rule_id": "A99", "status": "PASS"}])
    assert summary["unknown_rules"] == ["A99"]


def test_coverage_metrics():
    metrics = coverage_metrics(PAGES, RESULTS)
    assert metrics["page_coverage"] == 100.0
    assert metrics["rule_coverage"] == round(3 / len(RULE_IDS) * 100, 1)
    assert metrics["assertion_pass_rate"] == 75.0


def test_evidence_bundle_contains_all_sections():
    bundle = build_evidence_bundle(PAGES, RESULTS)
    assert set(bundle) == {"page_map", "rule_results", "coverage"}


def test_invalid_pages_rejected():
    with pytest.raises(AssetMapError):
        build_page_map([])
