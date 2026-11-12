"""M6 / TA-034.2：Asset-map 接入平台（页面地图 + 24 准则 + 覆盖率三指标）。"""
from __future__ import annotations

from typing import Any

RULE_IDS: tuple[str, ...] = tuple(f"A{i:02d}" for i in range(1, 25))


class AssetMapError(ValueError):
    pass


def build_page_map(pages: list[dict[str, Any]]) -> dict[str, Any]:
    if not pages:
        raise AssetMapError("pages 不能为空")
    nodes = []
    seen = set()
    for page in pages:
        path = str(page.get("path") or "").strip()
        if not path:
            raise AssetMapError("页面缺少 path")
        if path in seen:
            continue
        seen.add(path)
        nodes.append({"id": path, "title": str(page.get("title") or path)})
    edges = []
    for page in pages:
        source = str(page.get("path") or "")
        for target in page.get("links") or []:
            if target in seen and source:
                edges.append({"from": source, "to": str(target)})
    return {"nodes": nodes, "edges": edges}


def group_rule_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_rule = {
        rule: {"total": 0, "passed": 0, "failed": 0} for rule in RULE_IDS
    }
    unknown: set[str] = set()
    for result in results:
        rule = str(result.get("rule_id") or "").upper()
        if rule not in by_rule:
            unknown.add(rule or "<empty>")
            continue
        status = str(result.get("status") or "").upper()
        by_rule[rule]["total"] += 1
        if status == "PASS":
            by_rule[rule]["passed"] += 1
        else:
            by_rule[rule]["failed"] += 1
    return {
        "rules": by_rule,
        "unknown_rules": sorted(unknown),
        "total": len(results),
        "covered_rules": sum(1 for value in by_rule.values() if value["total"] > 0),
    }


def coverage_metrics(
    pages: list[dict[str, Any]], results: list[dict[str, Any]]
) -> dict[str, float]:
    page_map = build_page_map(pages)
    total_pages = len(page_map["nodes"])
    visited_pages = {
        str(result.get("page")) for result in results if result.get("page")
    }
    covered_pages = len(visited_pages & {node["id"] for node in page_map["nodes"]})
    rule_summary = group_rule_results(results)
    total_assertions = sum(value["total"] for value in rule_summary["rules"].values())
    passed_assertions = sum(value["passed"] for value in rule_summary["rules"].values())
    return {
        "page_coverage": round(covered_pages / total_pages * 100, 1) if total_pages else 0.0,
        "rule_coverage": round(rule_summary["covered_rules"] / len(RULE_IDS) * 100, 1),
        "assertion_pass_rate": round(
            passed_assertions / total_assertions * 100, 1
        ) if total_assertions else 0.0,
    }


def build_evidence_bundle(
    pages: list[dict[str, Any]], results: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "page_map": build_page_map(pages),
        "rule_results": group_rule_results(results),
        "coverage": coverage_metrics(pages, results),
    }
