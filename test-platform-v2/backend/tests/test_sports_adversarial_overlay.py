"""Adversarial coverage contract for every inventory-level sports module."""
from __future__ import annotations

from scripts.generate_sports_adversarial_overlay import (
    build_overlay,
    load_inventory_modules,
)
from scripts.audit_sports_case_quality import audit_consolidated


def test_overlay_covers_every_inventory_module_with_both_risk_classes():
    modules = load_inventory_modules()
    overlay = build_overlay(modules)

    assert len(modules) == 38
    assert set(overlay) == set(modules)
    for module, cases in overlay.items():
        assert len(cases) == 2, module
        assert {case["adversarial_category"] for case in cases} == {
            "recovery",
            "repeat_concurrency",
        }


def test_overlay_cases_are_executable_negative_scenarios_with_invariants():
    overlay = build_overlay(load_inventory_modules())

    for module, cases in overlay.items():
        for case in cases:
            assert case["case_id"].startswith("SP-B130-")
            assert case["positive_negative"] == "negative"
            assert case["preconditions"].strip(), module
            assert len(case["steps"]) >= 3, module
            assert all(step["desc"].strip() and step["expected"].strip() for step in case["steps"])
            assert "可重试" in case["expected_result"] or "仅一次" in case["expected_result"]
            assert "对抗性" in case["tags"]


def test_consolidated_asset_passes_case_quality_gate():
    report = audit_consolidated()

    assert report["status"] == "pass"
    assert report["totals"]["cases"] == 7879
    assert report["totals"]["unique_case_ids"] == 7879
    assert report["coverage"]["paired_inventory_modules"] == "38/38"
    assert report["coverage"]["adversarial_modules"] == "38/38"
    assert report["coverage"]["non_happy_ratio"] >= 0.45
    assert report["quality_issues"] == {
        "missing_title": 0,
        "missing_preconditions": 0,
        "invalid_steps": 0,
        "missing_expected_result": 0,
        "duplicate_case_ids": 0,
        "terminal_channel_taxonomy_nodes": 0,
        "source_module_mismatches": 0,
    }
