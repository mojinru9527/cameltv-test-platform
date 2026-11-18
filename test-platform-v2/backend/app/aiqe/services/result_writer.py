"""AUD-007：节点执行结果的断言持久化（唯一写入口）。

职责：
1. 把 ``AssertionOutcome`` 写入 ``run_assertion_results``（按 attempt+assertion_key 幂等）；
2. 按 required 断言聚合出 Node 终态（Driver 的 ``status=success`` 不再直接等于 Case PASS）；
3. 写 ``assertion.evaluated`` 事件，供 Run Console / 质量门禁只读消费。
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.assertions.engine import (
    AssertionOutcome,
    aggregate,
    evaluate_all,
    node_status_from_aggregate,
)
from app.aiqe.assertions.observation import Observation
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt
from app.aiqe.redaction import redact_mapping


def latest_attempt(db: Session, node_run_id: str) -> StepAttempt | None:
    return db.scalar(
        select(StepAttempt)
        .where(StepAttempt.node_run_id == node_run_id)
        .order_by(StepAttempt.attempt_no.desc())
    )


def persist_assertions(
    db: Session, *, step_attempt_id: str, outcomes: list[AssertionOutcome]
) -> list[RunAssertionResult]:
    """同一 attempt 内按 assertion_key 幂等 upsert。"""
    rows: list[RunAssertionResult] = []
    for outcome in outcomes:
        existing = db.scalar(
            select(RunAssertionResult).where(
                RunAssertionResult.step_attempt_id == step_attempt_id,
                RunAssertionResult.assertion_key == outcome.assertion_key,
            )
        )
        row = existing or RunAssertionResult(
            step_attempt_id=step_attempt_id,
            assertion_key=outcome.assertion_key,
            assertion_type=outcome.operator or "unknown",
        )
        row.assertion_type = outcome.operator or "unknown"
        row.status = outcome.status
        row.expected_json = redact_mapping(outcome.expected)
        row.actual_json = redact_mapping(outcome.actual_redacted)
        row.diff_json = redact_mapping(outcome.detail)
        row.evaluated_by = "deterministic"
        row.oracle_type = outcome.oracle_type or None
        row.oracle_id = outcome.oracle_id or None
        row.oracle_revision = outcome.oracle_revision
        row.evaluator_key = outcome.evaluator_key
        row.evaluator_version = outcome.evaluator_version
        row.source_ref = outcome.source_ref or None
        row.required = bool(outcome.required)
        row.duration_ms = int(outcome.duration_ms or 0)
        row.evaluated_at = outcome.evaluated_at or datetime.now(UTC)
        if existing is None:
            db.add(row)
        rows.append(row)
    db.flush()
    return rows


def specs_for_node(node: NodeRun) -> list[dict[str, Any]]:
    """节点断言：显式 ``assertions`` 优先；``expected_status`` 作为兼容简写。"""
    input_ref = dict(node.input_ref or {})
    specs = input_ref.get("assertions")
    if isinstance(specs, list) and specs:
        return [dict(item) for item in specs if isinstance(item, dict)]
    expected = input_ref.get("expected_status")
    if expected is not None:
        return [
            {
                "assertion_key": "http.status",
                "source": "http_status",
                "operator": "equals",
                "expected": int(expected),
                "required": True,
            }
        ]
    return []


def observation_from_payload(payload: dict[str, Any] | None) -> Observation | None:
    """把 Driver 的 observation 载荷转成 Observation（支持 http / db 两类来源）。"""
    if not isinstance(payload, dict):
        return None
    source = str(payload.get("source") or "http_response")
    if source in {"db_query", "db"}:
        return Observation(
            source="db_query",
            db_rows=tuple(payload.get("db_rows") or ()),
            error=payload.get("error"),
        )
    return Observation.from_http(
        status_code=payload.get("status_code"),
        headers=payload.get("headers") or {},
        text=str(payload.get("text") or ""),
        body=payload.get("body"),
        duration_ms=payload.get("duration_ms"),
        correlation_id=payload.get("correlation_id"),
        error=payload.get("error"),
    )


def observation_from_detail(detail: dict[str, Any] | None) -> Observation | None:
    payload = (detail or {}).get("observation")
    return observation_from_payload(payload if isinstance(payload, dict) else None)


def evaluate_node_assertions(
    db: Session,
    *,
    run_id: str,
    node: NodeRun,
    observation: Observation | None,
    driver_status: str | None = None,
    driver_error: str | None = None,
) -> tuple[str | None, str | None, list[AssertionOutcome]]:
    """评估并持久化；返回 ``(node_status, error_class, outcomes)``。

    无断言时返回 ``(None, None, [])``，由调用方沿用 Driver 结论（兼容旧 Workflow）。
    安全策略拒绝（Driver BLOCKED）时断言只能是 NOT_EVALUATED，**节点仍为 BLOCKED**，
    不能被误升级为 ERROR（AUD-001 §9）。
    """
    specs = specs_for_node(node)
    if not specs:
        return None, None, []
    observation = observation or Observation(source="unknown", error="DRIVER_ERROR")
    outcomes = evaluate_all(specs, observation)
    attempt = latest_attempt(db, node.id)
    if attempt is not None:
        persist_assertions(db, step_attempt_id=attempt.id, outcomes=outcomes)
        _emit_assertion_event(
            db,
            run_id=run_id,
            node=node,
            outcomes=outcomes,
            aggregate_status=aggregate(outcomes),
        )
    aggregate_status = aggregate(outcomes)
    if driver_status == "BLOCKED":
        return "BLOCKED", driver_error, outcomes
    mapped_status, mapped_error = node_status_from_aggregate(aggregate_status)
    return mapped_status, mapped_error, outcomes


def _emit_assertion_event(
    db: Session,
    *,
    run_id: str,
    node: NodeRun,
    outcomes: list[AssertionOutcome],
    aggregate_status: str,
) -> None:
    from app.aiqe.services import dag_scheduler

    dag_scheduler.emit_event(
        db,
        run_id=run_id,
        event_type="assertion.evaluated",
        payload={
            "node_key": node.node_key,
            "aggregate": aggregate_status,
            "total": len(outcomes),
            "failed": [item.assertion_key for item in outcomes if item.status == "FAIL"],
            "blocked": [item.assertion_key for item in outcomes if item.status == "BLOCKED"],
            "unknown": [item.assertion_key for item in outcomes if item.status == "UNKNOWN"],
            "results": [item.payload() for item in outcomes][:50],
        },
        producer_event_id=f"{node.id}:{int(node.attempt_count or 0)}:assertion.evaluated",
        node_run_id=node.id,
    )


__all__ = [
    "evaluate_node_assertions",
    "latest_attempt",
    "observation_from_detail",
    "persist_assertions",
    "specs_for_node",
]
