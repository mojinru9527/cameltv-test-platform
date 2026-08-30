"""AITDE V3.8 scenario-gap detector tests (V38-010).

Invariant: gap candidates are proposal-only — they never write a formal Scenario
Expected and must go through Tester Review → Change Proposal → New Version.
"""

from __future__ import annotations

from app.modules.aitde.ai_closed_loop import service
from app.modules.aitde.common.enums import GapCandidateStatus, ScenarioGapType


def test_detect_gap_creates_proposal(db):
    result = service.ScenarioGapDetector.detect(
        db,
        mission_id=7,
        inputs=[
            {
                "gap_type": ScenarioGapType.PROD_NEW_STATE.value,
                "title": "新支付状态未覆盖",
                "risk_level": "P1",
            }
        ],
    )
    assert result["created"] == 1
    candidate = result["candidates"][0]
    assert candidate["status"] == GapCandidateStatus.OPEN.value
    assert candidate["gap_type"] == ScenarioGapType.PROD_NEW_STATE.value


def test_gap_list_and_convert(db):
    service.ScenarioGapDetector.detect(db, 7, [{"title": "gap-1"}])
    gaps = service.ScenarioGapDetector.list(db, 7)
    assert len(gaps) == 1
    converted = service.ScenarioGapDetector.convert(db, gaps[0]["id"], "新用例", "P2")
    assert converted["converted"] is True
    assert "proposal only" in converted["note"]


def test_gap_cannot_convert_twice(db):
    service.ScenarioGapDetector.detect(db, 7, [{"title": "gap-1"}])
    gaps = service.ScenarioGapDetector.list(db, 7)
    service.ScenarioGapDetector.convert(db, gaps[0]["id"], "t", "P2")
    try:
        service.ScenarioGapDetector.convert(db, gaps[0]["id"], "t", "P2")
        assert False, "already-converted gap must not convert again"
    except ValueError:
        pass
