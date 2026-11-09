"""M1 / TA-005：TestRun 状态机单测（13 号 §5.1）。"""
from __future__ import annotations

import pytest

from app.aiqe.models.run import TestRun
from app.aiqe.services.run_state import (
    OUTCOMES,
    InvalidStateTransition,
    apply_transition,
    can_transition,
    transition,
)

LEGAL = [
    ("DRAFT", "VALIDATING", None),
    ("VALIDATING", "QUEUED", None),
    ("QUEUED", "RUNNING", None),
    ("RUNNING", "WAITING_HUMAN", None),
    ("WAITING_HUMAN", "RUNNING", None),
    ("RUNNING", "TRIAGING", None),
    ("TRIAGING", "RUNNING", None),
    ("TRIAGING", "COMPLETED", "PASS"),
    ("RUNNING", "COMPLETED", "FAIL"),
    ("RUNNING", "COMPLETED", "INCOMPLETE"),
    ("RUNNING", "COMPLETED", "UNKNOWN"),
    ("DRAFT", "CANCELED", None),
    ("RUNNING", "BLOCKED", None),
    ("QUEUED", "ERROR", None),
]

ILLEGAL = [
    ("DRAFT", "RUNNING"),
    ("DRAFT", "QUEUED"),
    ("VALIDATING", "RUNNING"),
    ("QUEUED", "COMPLETED"),
    ("WAITING_HUMAN", "COMPLETED"),
    ("COMPLETED", "RUNNING"),
    ("BLOCKED", "RUNNING"),
    ("CANCELED", "QUEUED"),
    ("ERROR", "DRAFT"),
    ("RUNNING", "RUNNING"),
]


@pytest.mark.parametrize(("current", "target", "outcome"), LEGAL)
def test_legal_transitions(current, target, outcome):
    assert transition(current, target, outcome=outcome) == target
    assert can_transition(current, target, outcome=outcome) is True


@pytest.mark.parametrize(("current", "target"), ILLEGAL)
def test_illegal_transitions_raise(current, target):
    with pytest.raises(InvalidStateTransition):
        transition(current, target)
    assert can_transition(current, target) is False


def test_unknown_state_raises():
    with pytest.raises(InvalidStateTransition):
        transition("NOPE", "RUNNING")
    with pytest.raises(InvalidStateTransition):
        transition("DRAFT", "NOPE")


def test_completed_requires_outcome():
    with pytest.raises(InvalidStateTransition):
        transition("RUNNING", "COMPLETED")
    with pytest.raises(InvalidStateTransition):
        transition("RUNNING", "COMPLETED", outcome="ok")
    for outcome in OUTCOMES:
        assert transition("RUNNING", "COMPLETED", outcome=outcome) == "COMPLETED"


@pytest.mark.parametrize("target", ["BLOCKED", "CANCELED", "ERROR"])
def test_terminal_without_outcome(target):
    assert transition("RUNNING", target) == target
    with pytest.raises(InvalidStateTransition):
        transition("RUNNING", target, outcome="PASS")


def test_non_completed_rejects_outcome():
    with pytest.raises(InvalidStateTransition):
        transition("RUNNING", "WAITING_HUMAN", outcome="PASS")


def test_apply_transition_mutates_and_clears_outcome():
    run = TestRun(project_id=1, run_key="RUN-1", status="RUNNING", outcome=None)
    assert apply_transition(run, "COMPLETED", outcome="PASS") == "COMPLETED"
    assert run.status == "COMPLETED"
    assert run.outcome == "PASS"

    run2 = TestRun(project_id=1, run_key="RUN-2", status="RUNNING")
    apply_transition(run2, "BLOCKED")
    assert run2.status == "BLOCKED"
    assert run2.outcome is None
