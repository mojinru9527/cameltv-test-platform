"""M6 / TA-034：Sports 纵向验收 adapter 单测（含造 Bug→修复）。"""
from __future__ import annotations

from app.aiqe.adapters.cameltv_sports import CASES, SportsVerticalAdapter

BUG_CASE = "TC-AIQE-007"


def executor(fixed: bool):
    def run(case):
        if case.case_id == BUG_CASE and not fixed:
            return {"passed": False, "evidence": ["artifact:reconnect-trace"], "error": "重连超时"}
        return {"passed": True, "evidence": [f"artifact:{case.case_id.lower()}"]}

    return run


def test_ten_cases_defined():
    assert [case.case_id for case in CASES] == [f"TC-AIQE-{i:03d}" for i in range(1, 11)]


def test_all_cases_pass_when_healthy():
    summary = SportsVerticalAdapter(executor(fixed=True)).run()
    assert summary["total"] == 10
    assert summary["passed"] == 10
    assert summary["all_passed"] is True
    assert all(item["evidence"] for item in summary["results"])


def test_seeded_bug_is_discovered():
    summary = SportsVerticalAdapter(executor(fixed=False)).run()
    assert summary["all_passed"] is False
    failed = [item for item in summary["results"] if not item["passed"]]
    assert len(failed) == 1
    assert failed[0]["case_id"] == BUG_CASE
    assert failed[0]["evidence"] == ["artifact:reconnect-trace"]


def test_bug_fixed_all_green():
    summary = SportsVerticalAdapter(executor(fixed=True)).run()
    assert summary["all_passed"] is True
    assert summary["failed"] == 0
