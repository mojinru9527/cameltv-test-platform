"""V1.6.2 状态语义单一事实源测试（FIX-007 基础）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/statuses.py"


def _load():
    spec = importlib.util.spec_from_file_location("aiqe_statuses", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_only_pass_counts_as_pass():
    assert MODULE.is_pass("PASS")
    for status in ("SEMI_AUTOMATIC", "PARTIAL", "WAIVED", "BLOCKED", "NOT_RUN", "NOT_PROVEN", "FAIL", "UNKNOWN"):
        assert not MODULE.is_pass(status), status


def test_legacy_semi_automatic_maps_to_partial_only():
    assert MODULE.normalize("SEMI_AUTOMATIC") == "PARTIAL"
    assert MODULE.normalize("manual") == "PARTIAL"
    assert MODULE.normalize("SCREENSHOT_ONLY") == "PARTIAL"


def test_unknown_status_is_unknown_not_pass():
    assert MODULE.normalize("totally-new-status") == "UNKNOWN"
    assert not MODULE.is_pass("totally-new-status")


def test_aggregate_weakest_coverage_and_fail_dominates():
    assert MODULE.aggregate(["PASS", "PASS"]) == "PASS"
    assert MODULE.aggregate(["PASS", "PARTIAL"]) == "PARTIAL"
    assert MODULE.aggregate(["PASS", "BLOCKED"]) == "BLOCKED"
    assert MODULE.aggregate(["PASS", "NOT_RUN"]) == "NOT_RUN"
    assert MODULE.aggregate(["BLOCKED", "FAIL"]) == "FAIL"
    assert MODULE.aggregate([]) == "NOT_PROVEN"
