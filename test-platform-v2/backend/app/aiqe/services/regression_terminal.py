"""AUD-010：Regression 终态同步 / Before-After 对比 / 人工关闭建议。

v1.5 §02 AUD-010：

- 唯一 ``RunTerminalEventHandler``：读 Run 终态事件 → 幂等更新 DefectRegression；
- 聚合规则：required 断言 FAIL → FAIL；缺能力/部署不一致 → BLOCKED；证据不足 → UNKNOWN；
- 生成不可变 ``RunComparisonSnapshot``；
- **不自动关闭缺陷**，只给 ``READY_FOR_HUMAN_CLOSE`` / ``NEEDS_MORE_FIX`` 建议。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.artifact import RunArtifact
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.models.defect import DefectRegression, RunComparisonSnapshot

REGRESSION_STATUSES: tuple[str, ...] = (
    "QUEUED",
    "RUNNING",
    "PASS",
    "FAIL",
    "BLOCKED",
    "UNKNOWN",
    "CANCELLED",
)
SUGGESTIONS: dict[str, str] = {
    "PASS": "READY_FOR_HUMAN_CLOSE",
    "FAIL": "NEEDS_MORE_FIX",
    "BLOCKED": "NEEDS_MORE_FIX",
    "UNKNOWN": "INCONCLUSIVE",
    "CANCELLED": "INCONCLUSIVE",
}


@dataclass
class TerminalHandleResult:
    regression_id: int | None = None
    status: str = ""
    suggestion: str = ""
    comparison_id: str | None = None
    skipped: bool = False
    reason: str = ""
    changed: bool = False

    def payload(self) -> dict[str, Any]:
        return {
            "regression_id": self.regression_id,
            "status": self.status,
            "suggestion": self.suggestion,
            "comparison_id": self.comparison_id,
            "skipped": self.skipped,
            "reason": self.reason,
            "changed": self.changed,
        }


def _assertion_rows(db: Session, run_id: str) -> list[tuple[RunAssertionResult, NodeRun]]:
    rows = db.execute(
        select(RunAssertionResult, NodeRun)
        .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
        .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
        .where(NodeRun.run_id == run_id)
    ).all()
    return [(row[0], row[1]) for row in rows]


def aggregate_regression_status(
    db: Session, run: TestRun
) -> tuple[str, dict[str, Any], list[str], list[str]]:
    """返回 ``(status, summary, failing_refs, blocked_refs)``。"""
    assertions = _assertion_rows(db, run.id)
    failing = [
        f"{node.node_key}:{assertion.assertion_key}"
        for assertion, node in assertions
        if assertion.status == "FAIL" and bool(assertion.required)
    ]
    blocked = [
        f"{node.node_key}:{assertion.assertion_key}"
        for assertion, node in assertions
        if assertion.status in {"BLOCKED", "ERROR", "NOT_EVALUATED"} and bool(assertion.required)
    ]
    nodes = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run.id)))
    node_blocked = [node.node_key for node in nodes if node.status == "BLOCKED"]
    summary = {
        "run_status": run.status,
        "run_outcome": run.outcome,
        "assertions_total": len(assertions),
        "assertions_failed": len(failing),
        "assertions_blocked": len(blocked),
        "nodes_total": len(nodes),
        "nodes_blocked": node_blocked,
        "fixed_sha": run.commit_sha,
        "deployed_sha": (run.environment_snapshot_json or {}).get("deployed_sha", ""),
    }
    if run.status == "CANCELED":
        return "CANCELLED", summary, failing, blocked
    if run.status == "ERROR":
        return "UNKNOWN", summary, failing, blocked
    if not assertions and run.outcome == "PASS":
        # 没有断言就无法证明业务通过（AUD-007：Driver 成功不等于 Case PASS）。
        summary["reason"] = "NO_REQUIRED_ASSERTIONS"
        return "UNKNOWN", summary, failing, blocked
    if failing:
        return "FAIL", summary, failing, blocked
    if run.outcome == "PASS":
        return "PASS", summary, failing, blocked
    if run.outcome == "INCOMPLETE" or blocked or node_blocked:
        return "BLOCKED", summary, failing, blocked
    if run.outcome == "FAIL":
        return "FAIL", summary, failing, blocked
    return "UNKNOWN", summary, failing, blocked


def build_comparison_snapshot(
    db: Session,
    *,
    project_id: int,
    regression: DefectRegression | None,
    source_run: TestRun | None,
    regression_run: TestRun,
    outcome: str,
) -> RunComparisonSnapshot:
    current_assertions = {
        f"{node.node_key}:{assertion.assertion_key}": assertion.status
        for assertion, node in _assertion_rows(db, regression_run.id)
    }
    previous_assertions: dict[str, str] = {}
    if source_run is not None:
        previous_assertions = {
            f"{node.node_key}:{assertion.assertion_key}": assertion.status
            for assertion, node in _assertion_rows(db, source_run.id)
        }
    new_failures = sorted(
        key for key, status in current_assertions.items()
        if status in {"FAIL", "BLOCKED", "ERROR"} and previous_assertions.get(key) == "PASS"
    )
    fixed_failures = sorted(
        key for key, status in current_assertions.items()
        if status == "PASS" and previous_assertions.get(key) in {"FAIL", "BLOCKED", "ERROR"}
    )
    still_failing = sorted(
        key for key, status in current_assertions.items()
        if status in {"FAIL", "BLOCKED", "ERROR"} and previous_assertions.get(key) in {"FAIL", "BLOCKED", "ERROR"}
    )
    node_diff = {
        "current": _node_statuses(db, regression_run.id),
        "previous": _node_statuses(db, source_run.id) if source_run is not None else {},
    }
    artifacts = list(
        db.scalars(select(RunArtifact).where(RunArtifact.run_id == regression_run.id))
    )
    evidence_refs = [f"artifact:{row.id}" for row in artifacts]
    snapshot = RunComparisonSnapshot(
        id=str(uuid.uuid4()),
        project_id=int(project_id),
        regression_id=regression.id if regression is not None else None,
        defect_id=regression.defect_id if regression is not None else None,
        source_run_id=source_run.id if source_run is not None else None,
        regression_run_id=regression_run.id,
        fixed_sha=(regression.fixed_sha if regression is not None else regression_run.commit_sha)[:64],
        deployed_sha=str((regression.deployed_sha if regression is not None else "") or "")[:64],
        workflow_checksum=(
            regression.workflow_checksum if regression is not None else None
        ),
        outcome=outcome,
        assertion_diff_json={
            "current": current_assertions,
            "previous": previous_assertions,
            "new_failures": new_failures,
            "fixed_failures": fixed_failures,
            "still_failing": still_failing,
        },
        node_attempt_diff_json=node_diff,
        evidence_refs_json=evidence_refs,
        new_failures_json=new_failures,
        fixed_failures_json=fixed_failures,
        blocked_json=[
            key for key, status in current_assertions.items() if status in {"BLOCKED", "ERROR"}
        ],
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _node_statuses(db: Session, run_id: str) -> dict[str, str]:
    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))
    return {row.node_key: row.status for row in rows}


def handle_run_terminal(
    db: Session, *, run_id: str, event_id: str | None = None
) -> TerminalHandleResult:
    """Run 终态处理器：幂等、只更新回归与对比快照，绝不改缺陷状态。"""
    run = db.get(TestRun, run_id)
    if run is None:
        return TerminalHandleResult(skipped=True, reason="RUN_NOT_FOUND")
    regression = db.scalar(
        select(DefectRegression)
        .where(DefectRegression.verification_run_id == run_id)
        .with_for_update()
    )
    if regression is None:
        return TerminalHandleResult(skipped=True, reason="NO_REGRESSION")
    if regression.completed_at is not None:
        return TerminalHandleResult(
            regression_id=regression.id,
            status=regression.status,
            suggestion=regression.suggestion or "",
            comparison_id=regression.comparison_snapshot_id,
            skipped=True,
            reason="ALREADY_HANDLED",
        )

    status, summary, failing, blocked = aggregate_regression_status(db, run)
    source_run = (
        db.get(TestRun, regression.source_run_id) if regression.source_run_id else None
    )
    snapshot = build_comparison_snapshot(
        db,
        project_id=int(regression_owner_project(db, regression)),
        regression=regression,
        source_run=source_run,
        regression_run=run,
        outcome=status,
    )
    suggestion = SUGGESTIONS.get(status, "INCONCLUSIVE")
    regression.status = status
    regression.completed_at = datetime.now(UTC)
    regression.terminal_summary_json = {
        **summary,
        "event_id": event_id,
        "failing": failing[:200],
        "blocked": blocked[:200],
    }
    regression.failing_case_ids_json = failing[:200]
    regression.assertion_refs_json = sorted(
        set((regression.assertion_refs_json or []) + failing + blocked)
    )
    regression.evidence_refs_json = list(snapshot.evidence_refs_json or [])
    regression.comparison_snapshot_id = snapshot.id
    regression.suggestion = suggestion
    db.flush()

    from app.aiqe.services import dag_scheduler

    dag_scheduler.emit_event(
        db,
        run_id=run.id,
        event_type="regression.completed" if status in {"PASS", "FAIL"} else "regression.updated",
        payload={
            "regression_id": regression.id,
            "status": status,
            "suggestion": suggestion,
            "comparison_id": snapshot.id,
            "failing": failing[:50],
            "event_id": event_id,
        },
        producer_event_id=f"regression:{regression.id}:terminal:{run.id}",
    )
    db.flush()
    return TerminalHandleResult(
        regression_id=regression.id,
        status=status,
        suggestion=suggestion,
        comparison_id=snapshot.id,
        changed=True,
    )


def regression_owner_project(db: Session, regression: DefectRegression) -> int:
    from app.models.defect import Defect

    defect = db.get(Defect, regression.defect_id)
    return int(defect.project_id or 0) if defect is not None else 0


def consume_terminal_events(db: Session, *, limit: int = 50) -> list[TerminalHandleResult]:
    """从 Outbox 消费 ``run.completed`` 事件并驱动回归终态同步。"""
    from app.aiqe.models.event import EventOutbox, RunEvent

    rows = db.execute(
        select(RunEvent)
        .join(EventOutbox, EventOutbox.run_event_id == RunEvent.id)
        .where(
            EventOutbox.dispatched_at.is_(None),
            RunEvent.event_type.in_(["run.completed", "run.failed", "run.blocked"]),
        )
        .order_by(RunEvent.id)
        .limit(limit)
    ).all()
    results: list[TerminalHandleResult] = []
    for (event,) in rows:
        results.append(handle_run_terminal(db, run_id=event.run_id, event_id=event.id))
        outbox = db.scalar(
            select(EventOutbox).where(EventOutbox.run_event_id == event.id)
        )
        if outbox is not None:
            outbox.dispatched_at = datetime.now(UTC)
            outbox.retry_count = int(outbox.retry_count or 0) + 1
    db.flush()
    return results


__all__ = [
    "REGRESSION_STATUSES",
    "SUGGESTIONS",
    "TerminalHandleResult",
    "aggregate_regression_status",
    "build_comparison_snapshot",
    "consume_terminal_events",
    "handle_run_terminal",
]
