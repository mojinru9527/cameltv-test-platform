"""AUD-007：Assertion Engine（唯一判定入口）。

v1.5 §01 AUD-007 规则：

- P0/P1 无 Oracle → ``BLOCKED``（NEEDS_HUMAN），不得生成猜测断言；
- 字段缺失、类型不匹配、非法表达式 → ``FAIL``/``UNKNOWN``，**不得默认 PASS**；
- evaluator 自身异常 → ``ERROR``（不伪装成产品 FAIL）；
- 未注册算子 → ``ERROR``；
- 聚合只看 required 断言；``NOT_EVALUATED`` 表示前置失败导致未执行。
"""
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.aiqe.assertions.observation import Observation
from app.aiqe.assertions.registry import (
    OPERATOR_VERSION,
    OperatorError,
    evaluate_operator,
)
from app.aiqe.redaction import redact_mapping

EVALUATOR_KEY = "aiqe.assertion.engine"
EVALUATOR_VERSION = f"1.0.0+op{OPERATOR_VERSION}"

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"
ERROR = "ERROR"
NOT_EVALUATED = "NOT_EVALUATED"

RESULTS: frozenset[str] = frozenset({PASS, FAIL, BLOCKED, UNKNOWN, ERROR, NOT_EVALUATED})
ORACLE_REQUIRED_PRIORITIES: frozenset[str] = frozenset({"P0", "P1"})


@dataclass(frozen=True)
class AssertionOutcome:
    assertion_key: str
    status: str
    operator: str
    source: str
    source_ref: str
    expected: Any = None
    actual_redacted: Any = None
    required: bool = True
    severity: str = ""
    oracle_type: str = ""
    oracle_id: str = ""
    oracle_revision: int | None = None
    evaluator_key: str = EVALUATOR_KEY
    evaluator_version: str = EVALUATOR_VERSION
    duration_ms: int = 0
    evaluated_at: datetime | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {
            "assertion_key": self.assertion_key,
            "status": self.status,
            "operator": self.operator,
            "source": self.source,
            "source_ref": self.source_ref,
            "expected": redact_mapping(self.expected),
            "actual_redacted": redact_mapping(self.actual_redacted),
            "required": self.required,
            "severity": self.severity,
            "oracle_type": self.oracle_type,
            "oracle_id": self.oracle_id,
            "oracle_revision": self.oracle_revision,
            "evaluator_key": self.evaluator_key,
            "evaluator_version": self.evaluator_version,
            "duration_ms": self.duration_ms,
            "evaluated_at": (self.evaluated_at or datetime.now(UTC)).isoformat(),
            "detail": redact_mapping(self.detail),
        }


class OracleRegistry:
    """已批准 Oracle 集合；未提供时仅校验"存在 oracle_ref"。"""

    def __init__(self, approved_ids: Iterable[str] = ()) -> None:
        self.approved = {str(item) for item in approved_ids if str(item)}

    def is_approved(self, oracle_type: str, oracle_id: str) -> bool:
        return f"{oracle_type}:{oracle_id}" in self.approved or oracle_id in self.approved


def _oracle_fields(spec: Mapping[str, Any]) -> tuple[str, str, int | None]:
    ref = spec.get("oracle_ref")
    if isinstance(ref, Mapping):
        return (
            str(ref.get("type") or ""),
            str(ref.get("id") or ""),
            int(ref["revision"]) if ref.get("revision") is not None else None,
        )
    return "", "", None


def _source_ref(spec: Mapping[str, Any]) -> str:
    explicit = str(spec.get("source_ref") or "").strip()
    if explicit:
        return explicit
    source = str(spec.get("source") or "http_body")
    path = str(spec.get("path") or "")
    return f"{source}:{path}" if path else source


def _assertion_key(spec: Mapping[str, Any], index: int) -> str:
    explicit = str(spec.get("assertion_key") or "").strip()
    return explicit or f"assertion-{index + 1}"


def _assertion_digest(spec: Mapping[str, Any]) -> str:
    import json

    payload = json.dumps(dict(spec), sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _maybe_redact_actual(spec: Mapping[str, Any], value: Any) -> Any:
    """断言 actual 若来自敏感字段（如 access_token），持久化前必须打码。"""
    from app.aiqe.redaction import CLASSIFIER, REDACTED

    path = str(spec.get("path") or "")
    source = str(spec.get("source") or "")
    leaf = path.rsplit(".", 1)[-1].split("[", 1)[0] if path else ""
    if CLASSIFIER.is_sensitive_key(leaf) or (
        source in {"http_header", "db_query", "db"} and CLASSIFIER.is_sensitive_key(leaf)
    ):
        return REDACTED
    return value


def evaluate_assertion(
    spec: Mapping[str, Any],
    observation: Observation,
    *,
    oracle_registry: OracleRegistry | None = None,
    index: int = 0,
    now: datetime | None = None,
) -> AssertionOutcome:
    started = time.monotonic()
    key = _assertion_key(spec, index)
    operator = str(spec.get("operator") or "equals").lower()
    source = str(spec.get("source") or "http_body")
    expected = spec.get("expected")
    required = bool(spec.get("required", True))
    severity = str(spec.get("severity") or spec.get("priority") or "")
    oracle_type, oracle_id, oracle_revision = _oracle_fields(spec)
    source_ref = _source_ref(spec)

    def _finish(status: str, actual: Any = None, detail: dict | None = None) -> AssertionOutcome:
        return AssertionOutcome(
            assertion_key=key,
            status=status,
            operator=operator,
            source=source,
            source_ref=source_ref,
            expected=expected,
            actual_redacted=_maybe_redact_actual(spec, actual),
            required=required,
            severity=severity,
            oracle_type=oracle_type,
            oracle_id=oracle_id,
            oracle_revision=oracle_revision,
            duration_ms=int((time.monotonic() - started) * 1000),
            evaluated_at=now or datetime.now(UTC),
            detail={"assertion_digest": _assertion_digest(spec), **(detail or {})},
        )

    # 1) Oracle 前置：P0/P1 无 Oracle 时不得判定产品 PASS/FAIL
    needs_oracle = severity.upper() in ORACLE_REQUIRED_PRIORITIES
    if needs_oracle and not oracle_id:
        return _finish(BLOCKED, detail={"reason": "ORACLE_MISSING", "severity": severity})
    if needs_oracle and oracle_registry is not None and not oracle_registry.is_approved(
        oracle_type, oracle_id
    ):
        return _finish(
            BLOCKED,
            detail={
                "reason": "ORACLE_NOT_APPROVED",
                "oracle_type": oracle_type,
                "oracle_id": oracle_id,
            },
        )

    # 2) Driver 失败：断言不执行（NOT_EVALUATED），不等于产品 FAIL
    if observation.error:
        return _finish(
            NOT_EVALUATED, detail={"reason": "OBSERVATION_UNAVAILABLE", "error": observation.error}
        )

    # 3) 确定性评估
    try:
        result = evaluate_operator(spec, observation)
    except OperatorError as exc:
        return _finish(ERROR, detail={"reason": "OPERATOR_ERROR", "message": str(exc)})
    except Exception as exc:  # evaluator 自身异常必须为 ERROR
        return _finish(
            ERROR, detail={"reason": "EVALUATOR_EXCEPTION", "message": f"{type(exc).__name__}: {exc}"}
        )

    if not result.found:
        # 「不存在」类断言：源值缺失正是其期望结果。
        if operator == "not_exists":
            return _finish(PASS, actual=None, detail={**result.detail, "missing_value": True})
        if operator == "exists" and spec.get("expected") in (None, False):
            return _finish(PASS, actual=None, detail={**result.detail, "missing_value": True})
        status = FAIL if required else UNKNOWN
        return _finish(status, actual=None, detail={**result.detail, "missing_value": True})
    return _finish(PASS if result.passed else FAIL, actual=result.actual, detail=result.detail)


def evaluate_all(
    assertions: Sequence[Mapping[str, Any]] | None,
    observation: Observation,
    *,
    oracle_registry: OracleRegistry | None = None,
    now: datetime | None = None,
) -> list[AssertionOutcome]:
    outcomes: list[AssertionOutcome] = []
    for index, raw in enumerate(assertions or []):
        if not isinstance(raw, Mapping):
            outcomes.append(
                AssertionOutcome(
                    assertion_key=f"assertion-{index + 1}",
                    status=ERROR,
                    operator="",
                    source="",
                    source_ref="",
                    required=True,
                    duration_ms=0,
                    evaluated_at=now or datetime.now(UTC),
                    detail={"reason": "INVALID_ASSERTION_SPEC"},
                )
            )
            continue
        outcomes.append(
            evaluate_assertion(raw, observation, oracle_registry=oracle_registry, index=index, now=now)
        )
    return outcomes


def aggregate(outcomes: Sequence[AssertionOutcome], *, required_only: bool = True) -> str:
    """按 required 断言聚合：ERROR/BLOCKED/FAIL/UNKNOWN 优先级从高到低。"""
    selected = [item for item in outcomes if item.required or not required_only]
    if not selected:
        return NOT_EVALUATED
    statuses = {item.status for item in selected}
    for status in (ERROR, BLOCKED, FAIL, UNKNOWN, NOT_EVALUATED):
        if status in statuses:
            return status
    return PASS


def node_status_from_aggregate(aggregate_status: str) -> tuple[str, str]:
    """把断言聚合结果映射为 NodeRun 终态 + error_class。"""
    mapping = {
        PASS: ("PASSED", ""),
        FAIL: ("FAILED", "ASSERTION_FAILED"),
        BLOCKED: ("BLOCKED", "ASSERTION_BLOCKED"),
        UNKNOWN: ("ERROR", "ASSERTION_UNKNOWN"),
        ERROR: ("ERROR", "ASSERTION_ERROR"),
        NOT_EVALUATED: ("ERROR", "ASSERTION_NOT_EVALUATED"),
    }
    return mapping.get(aggregate_status, ("ERROR", "ASSERTION_ERROR"))


def poll_until(
    evaluate: Callable[[], AssertionOutcome],
    *,
    timeout_ms: int,
    interval_ms: int = 500,
    sleep: Callable[[float], None] | None = None,
) -> tuple[AssertionOutcome, list[dict[str, Any]]]:
    """异步断言轮询：有明确 timeout 与采样记录，不会无限循环。"""
    import time as _time

    pause = sleep or _time.sleep
    budget = max(0, int(timeout_ms))
    interval = max(10, int(interval_ms))
    samples: list[dict[str, Any]] = []
    deadline = _time.monotonic() + budget / 1000
    while True:
        outcome = evaluate()
        samples.append({"at": (outcome.evaluated_at or datetime.now(UTC)).isoformat(), "status": outcome.status})
        if outcome.status in {PASS, FAIL, ERROR}:
            return outcome, samples
        if _time.monotonic() >= deadline:
            return outcome, samples
        pause(interval / 1000)


__all__ = [
    "BLOCKED",
    "ERROR",
    "EVALUATOR_KEY",
    "EVALUATOR_VERSION",
    "FAIL",
    "NOT_EVALUATED",
    "ORACLE_REQUIRED_PRIORITIES",
    "PASS",
    "RESULTS",
    "UNKNOWN",
    "AssertionOutcome",
    "OracleRegistry",
    "aggregate",
    "evaluate_all",
    "evaluate_assertion",
    "node_status_from_aggregate",
    "poll_until",
]
