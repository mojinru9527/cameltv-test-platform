"""AITDE V3.8 data-strategy advisor tests (V38-008/009).

Invariant: the advisor may suggest a priority order only; Policy / environment
access mode / approval requirement always take precedence.
"""

from __future__ import annotations

from app.modules.aitde.ai_closed_loop import service


def test_advisor_ranks_by_success_rate(db):
    service.StrategyPerformanceService.record(db, 1, "API", "api-builder", True, 120)
    service.StrategyPerformanceService.record(db, 1, "API", "api-builder", True, 90)
    service.StrategyPerformanceService.record(
        db, 1, "DB_FIXTURE", "db-fixture", False, 200
    )
    service.StrategyPerformanceService.record(db, 1, "EXISTING", "existing", True, 30)

    advice = service.DataStrategyAdvisor.advise(db, 1)
    # api-builder has highest success rate (2/2), then existing (1/1).
    assert advice["recommended_priority"][0] == "api-builder"
    assert advice["policy_override"] is True
    assert "always take precedence" in advice["note"]


def test_advisor_never_bypasses_policy(db):
    advice = service.DataStrategyAdvisor.advise(db, 1)
    # Empty table still yields a safe, policy-first recommendation.
    assert advice["policy_override"] is True
    assert advice["recommended_priority"] == []
