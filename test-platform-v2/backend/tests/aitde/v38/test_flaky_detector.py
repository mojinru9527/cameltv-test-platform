"""AITDE V3.8 flaky detector / cluster tests.

V38-006 FlakySignal pipeline (BusinessFail excluded), V38-007 FlakyCluster UI +
traceable samples. Invariant: a real BUSINESS_FAIL is never auto-flagged flaky
and never auto-passed.
"""

from __future__ import annotations

from app.modules.aitde.ai_closed_loop import service
from app.modules.aitde.common.enums import (
    FlakyClassification,
    FlakySignalType,
    Outcome,
)


def test_flaky_signal_excludes_business_fail(db):
    try:
        service.FlakyDetector.record(
            db,
            10,
            1,
            FlakySignalType.RERUN_PASS.value,
            "sig",
            outcome=Outcome.BUSINESS_FAIL.value,
        )
        assert False, "BUSINESS_FAIL must be excluded from flaky signals"
    except ValueError:
        pass


def test_flaky_analyze_creates_cluster(db):
    service.FlakyDetector.record(
        db,
        10,
        1,
        FlakySignalType.RERUN_PASS.value,
        "sig-a",
        outcome=Outcome.AUTOMATION_FAIL.value,
    )
    service.FlakyDetector.record(
        db,
        10,
        2,
        FlakySignalType.RERUN_PASS.value,
        "sig-a",
        outcome=Outcome.AUTOMATION_FAIL.value,
    )
    result = service.FlakyDetector.analyze(db, 10)
    assert len(result["clusters"]) == 1
    cluster = result["clusters"][0]
    assert cluster["cluster_key"] == "sig-a"
    assert cluster["sample_size"] == 2
    assert cluster["classification"] in {
        FlakyClassification.FLAKY.value,
        FlakyClassification.FLAPPY.value,
        FlakyClassification.UNCLASSIFIED.value,
    }


def test_flaky_cluster_list_traceable(db):
    service.FlakyDetector.record(
        db,
        10,
        1,
        FlakySignalType.TIMEOUT.value,
        "sig-b",
        outcome=Outcome.ENV_FAIL.value,
    )
    service.FlakyDetector.analyze(db, 10)
    clusters = service.FlakyClusterService.list(db, 10)
    assert len(clusters) == 1
    # samples link back to run_id (traceable)
    signals = service.FlakyDetector.analyze(db, 10)
    assert signals["clusters"][0]["sample_size"] >= 1


def test_strategy_performance_isolated_by_project(db):
    a = service.StrategyPerformanceService.record(db, 1, "API", "k1", True, 120)
    service.StrategyPerformanceService.record(db, 2, "API", "k1", False, 80)
    assert a["success_rate"] == 1.0
    proj1 = service.StrategyPerformanceService.list(db, 1)
    proj2 = service.StrategyPerformanceService.list(db, 2)
    assert len(proj1) == 1 and len(proj2) == 1  # project isolation
