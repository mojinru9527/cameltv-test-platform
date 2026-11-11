"""M5 / TA-031：Quality Gate 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.services.quality_gate import evaluate_cases, evaluate_stats


def case(priority: str, status: str):
    return {"priority": priority, "status": status}


def test_all_p0_pass():
    result = evaluate_cases([case("P0", "PASS"), case("P1", "FAIL")])
    assert result["gate_status"] == "PASS"
    assert result["p0_total"] == 1


@pytest.mark.parametrize("status", ["FAIL", "UNKNOWN", "NOT_RUN"])
def test_p0_not_passed_blocks_gate(status):
    result = evaluate_cases([case("P0", "PASS"), case("P0", status)])
    assert result["gate_status"] != "PASS"


def test_p0_fail_is_fail():
    assert evaluate_cases([case("P0", "FAIL")])["gate_status"] == "FAIL"


def test_p0_unknown_or_not_run_is_blocked():
    assert evaluate_cases([case("P0", "UNKNOWN")])["gate_status"] == "BLOCKED"
    assert evaluate_cases([case("P0", "NOT_RUN")])["gate_status"] == "BLOCKED"


def test_no_p0_blocked():
    result = evaluate_cases([case("P1", "PASS")])
    assert result["gate_status"] == "BLOCKED"
    assert result["reasons"]


def test_stats_gate():
    ok = evaluate_stats({"p0_total": 3, "p0_passed": 3})
    assert ok["gate_status"] == "PASS"
    blocked = evaluate_stats({"p0_total": 3, "p0_passed": 2, "p0_not_run": 1})
    assert blocked["gate_status"] == "BLOCKED"
    failed = evaluate_stats({"p0_total": 3, "p0_passed": 2, "p0_failed": 1})
    assert failed["gate_status"] == "FAIL"


def test_empty_stats_blocked():
    assert evaluate_stats({})["gate_status"] == "BLOCKED"
