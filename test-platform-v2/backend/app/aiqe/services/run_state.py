"""M1 / TA-005：TestRun 状态机（唯一入口）。

13 号 §5.1：

    DRAFT → VALIDATING → QUEUED → RUNNING
    RUNNING → WAITING_HUMAN / TRIAGING / COMPLETED
    WAITING_HUMAN → RUNNING
    TRIAGING → RUNNING / COMPLETED
    任意非终态 → BLOCKED / CANCELED / ERROR

规则：
- COMPLETED 必须有 outcome（PASS/FAIL/INCOMPLETE/UNKNOWN）；
- BLOCKED / CANCELED / ERROR 必须没有 outcome；
- 终态不可再迁移；同状态迁移非法；
- 所有迁移只能走 ``transition()``，非法迁移抛 ``InvalidStateTransition``。
"""
from __future__ import annotations

from app.aiqe.models.run import TestRun

RUN_STATUSES: tuple[str, ...] = (
    "DRAFT",
    "VALIDATING",
    "QUEUED",
    "RUNNING",
    "WAITING_HUMAN",
    "TRIAGING",
    "COMPLETED",
    "BLOCKED",
    "CANCELED",
    "ERROR",
)

OUTCOMES: tuple[str, ...] = ("PASS", "FAIL", "INCOMPLETE", "UNKNOWN")

TERMINAL_STATUSES: frozenset[str] = frozenset({"COMPLETED", "BLOCKED", "CANCELED", "ERROR"})

_ALLOWED: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"VALIDATING", "BLOCKED", "CANCELED", "ERROR"}),
    "VALIDATING": frozenset({"QUEUED", "BLOCKED", "CANCELED", "ERROR"}),
    "QUEUED": frozenset({"RUNNING", "BLOCKED", "CANCELED", "ERROR"}),
    "RUNNING": frozenset(
        {"WAITING_HUMAN", "TRIAGING", "COMPLETED", "BLOCKED", "CANCELED", "ERROR"}
    ),
    "WAITING_HUMAN": frozenset({"RUNNING", "BLOCKED", "CANCELED", "ERROR"}),
    "TRIAGING": frozenset({"RUNNING", "COMPLETED", "BLOCKED", "CANCELED", "ERROR"}),
    "COMPLETED": frozenset(),
    "BLOCKED": frozenset(),
    "CANCELED": frozenset(),
    "ERROR": frozenset(),
}


class InvalidStateTransition(ValueError):
    """非法状态迁移（13 号 §5.1 单测必须覆盖）。"""


def _validate_outcome(target: str, outcome: str | None) -> None:
    if target == "COMPLETED":
        if outcome not in OUTCOMES:
            raise InvalidStateTransition(
                f"COMPLETED 必须带合法 outcome（{OUTCOMES}），实际 {outcome!r}"
            )
        return
    if outcome is not None:
        raise InvalidStateTransition(f"{target} 不允许携带 outcome（实际 {outcome!r}）")


def can_transition(current: str, target: str, *, outcome: str | None = None) -> bool:
    """纯判定，不抛异常（UI 预判/测试用）。"""
    if current not in _ALLOWED or target not in RUN_STATUSES:
        return False
    if current == target:
        return False
    if target not in _ALLOWED[current]:
        return False
    if target == "COMPLETED":
        return outcome in OUTCOMES
    return outcome is None


def transition(current: str, target: str, *, outcome: str | None = None) -> str:
    """校验并返回目标状态；非法迁移抛 InvalidStateTransition。"""
    if current not in _ALLOWED:
        raise InvalidStateTransition(f"未知当前状态: {current!r}")
    if target not in RUN_STATUSES:
        raise InvalidStateTransition(f"未知目标状态: {target!r}")
    if current == target:
        raise InvalidStateTransition(f"状态未变化: {current}")
    if target not in _ALLOWED[current]:
        raise InvalidStateTransition(f"非法迁移: {current} → {target}")
    _validate_outcome(target, outcome)
    return target


def apply_transition(run: TestRun, target: str, *, outcome: str | None = None) -> str:
    """对 ORM 实例执行迁移（只改内存，不 commit）。"""
    new_status = transition(run.status, target, outcome=outcome)
    run.status = new_status
    if new_status == "COMPLETED":
        run.outcome = outcome
    else:
        run.outcome = None
    return new_status
