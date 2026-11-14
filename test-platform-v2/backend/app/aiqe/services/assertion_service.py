"""Assertion Runtime（FIX-002 / TA-009）。

职责边界：
- Driver 只采集事实（status/headers/body/locator/db/events），不决定业务 PASS；
- 本服务从 `DriverResult.data` 取 actual，执行机器断言，并写入
  `run_assertion_results`（失败 attempt 的结果永久保留）；
- `NOT_EVALUATED / BLOCKED` 永远不会被折算成 PASS；
- 断言引擎自身异常记 ERROR，不伪装成业务 FAIL。

Actuals 约定（由 `build_actuals` 生成）：
```
status_code, headers, body_text, json, duration_ms, url,
locators: {selector: {visible, count, text}},
db: {rows, row_count, columns, value},
events: [event_type, ...],
driver_status
```
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt
from app.aiqe.schemas.contracts import (
    AssertionOutcome,
    AssertionSpec,
    AssertionStatus,
    DriverResult,
)
from app.aiqe.services import jsonpath_subset
from app.aiqe.services.evidence_redactor import redact

try:  # JSON Schema 已在 requirements.lock 固定（jsonschema==4.26.0）
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError as JsonSchemaDefinitionError
    from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
except Exception:  # pragma: no cover - 运行环境缺依赖时必须显式 ERROR，不能静默 PASS
    Draft202012Validator = None  # type: ignore[assignment]
    JsonSchemaDefinitionError = JsonSchemaValidationError = Exception  # type: ignore[misc,assignment]

PASS: Final[AssertionStatus] = "PASS"
FAIL: Final[AssertionStatus] = "FAIL"
ERROR: Final[AssertionStatus] = "ERROR"
NOT_EVALUATED: Final[AssertionStatus] = "NOT_EVALUATED"
BLOCKED: Final[AssertionStatus] = "BLOCKED"

SUMMARY_STATUSES = frozenset({PASS, FAIL, ERROR, NOT_EVALUATED, BLOCKED})


class AssertionConfigError(ValueError):
    """断言配置非法（类型/路径/expected_ref）。"""


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def normalize_assertion(raw: Mapping[str, Any], index: int = 0) -> AssertionSpec:
    payload = _as_mapping(raw)
    key = str(
        payload.get("assertion_key")
        or payload.get("key")
        or f"assertion-{index + 1}"
    )
    oracle_layer = str(payload.get("oracle_layer") or "STD").upper()
    if oracle_layer not in {"REQ", "STD", "PATTERN"}:
        raise AssertionConfigError(f"非法 oracle_layer: {oracle_layer!r}")
    assertion_type = str(payload.get("type") or payload.get("assertion_type") or "").strip()
    if not assertion_type:
        raise AssertionConfigError(f"断言 {key} 缺少 type")
    schema = payload.get("schema")
    return AssertionSpec(
        assertion_key=key,
        schema_version=str(payload.get("schema_version") or "1.0"),
        oracle_layer=oracle_layer,  # type: ignore[arg-type]
        oracle_ref=str(payload.get("oracle_ref") or payload.get("rule_id") or ""),
        type=assertion_type,
        operator=str(payload.get("operator") or "eq"),
        expected=payload.get("expected"),
        expected_ref=payload.get("expected_ref"),
        actual_source=str(payload.get("actual_source") or ""),
        path=payload.get("path"),
        selector=payload.get("selector"),
        schema=schema,
        timeout_ms=int(payload.get("timeout_ms") or 0),
        severity=str(payload.get("severity") or "P1").upper(),  # type: ignore[arg-type]
        message=str(payload.get("message") or ""),
        **{
            k: v
            for k, v in payload.items()
            if k
            not in {
                "assertion_key",
                "key",
                "schema_version",
                "oracle_layer",
                "oracle_ref",
                "rule_id",
                "type",
                "assertion_type",
                "operator",
                "expected",
                "expected_ref",
                "actual_source",
                "path",
                "selector",
                "schema",
                "timeout_ms",
                "severity",
                "message",
            }
        },
    )


def normalize_assertions(raw_assertions: Iterable[Mapping[str, Any]] | None) -> list[AssertionSpec]:
    specs: list[AssertionSpec] = []
    for index, raw in enumerate(raw_assertions or []):
        if not isinstance(raw, Mapping):
            raise AssertionConfigError(f"assertion[{index}] 必须是对象")
        if str(raw.get("type") or "") == "exploratory":
            continue
        specs.append(normalize_assertion(raw, index))
    return specs


def build_actuals(result: DriverResult) -> dict[str, Any]:
    data = dict(result.data or {})
    body_text = data.get("body_text")
    if body_text is None:
        body_text = data.get("text")
    payload = data.get("json")
    if payload is None:
        payload = data.get("body_json")
    if payload is None and isinstance(body_text, str) and body_text.strip():
        try:
            payload = json.loads(body_text)
        except (TypeError, ValueError):
            payload = None
    return {
        "status_code": data.get("status_code"),
        "headers": data.get("headers") or {},
        "body_text": body_text if isinstance(body_text, str) else "",
        "json": payload,
        "duration_ms": result.duration_ms or data.get("duration_ms") or 0,
        "url": data.get("url") or data.get("final_url") or "",
        "locators": data.get("locators") or {},
        "db": data.get("db") or {},
        "events": data.get("events") or [],
        "driver_status": result.status,
        "raw": data,
    }


def _compare(actual: Any, expected: Any, operator: str) -> bool:
    op = (operator or "eq").strip().lower()
    try:
        if op in {"eq", "equals", "==", "is"}:
            return actual == expected
        if op in {"ne", "not_equals", "!="}:
            return actual != expected
        if op in {"gt", ">"}:
            return actual is not None and actual > expected
        if op in {"gte", "ge", ">="}:
            return actual is not None and actual >= expected
        if op in {"lt", "<"}:
            return actual is not None and actual < expected
        if op in {"lte", "le", "<="}:
            return actual is not None and actual <= expected
        if op in {"contains", "includes"}:
            return expected in actual if actual is not None else False
        if op in {"not_contains", "excludes"}:
            return expected not in actual if actual is not None else True
        if op == "startswith":
            return isinstance(actual, str) and actual.startswith(str(expected))
        if op == "endswith":
            return isinstance(actual, str) and actual.endswith(str(expected))
        if op == "regex":
            import re

            return isinstance(actual, str) and re.search(str(expected), actual) is not None
        if op == "in":
            return actual in expected if expected is not None else False
        if op == "not_in":
            return actual not in expected if expected is not None else True
        if op == "exists":
            return actual is not None
        if op == "not_exists":
            return actual is None
        if op == "is_null":
            return actual is None
        if op == "not_null":
            return actual is not None
    except TypeError:
        return False
    raise AssertionConfigError(f"未识别的断言算子: {operator!r}")


def _json_path_actual(data: Any, path: str) -> tuple[bool, Any]:
    try:
        return jsonpath_subset.first(data, path)
    except jsonpath_subset.JsonPathError as exc:
        raise AssertionConfigError(str(exc)) from exc


def _validate_json_schema(data: Any, schema: Mapping[str, Any]) -> tuple[bool, str]:
    if Draft202012Validator is None:
        return False, "jsonschema 不可用"
    try:
        Draft202012Validator.check_schema(dict(schema))
    except JsonSchemaDefinitionError as exc:
        raise AssertionConfigError(f"JSON Schema 非法: {exc.message}") from exc
    validator = Draft202012Validator(dict(schema))
    errors = sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    if not errors:
        return True, ""
    first = errors[0]
    return False, f"{'/'.join(str(part) for part in first.path)}: {first.message}"


def _resolve_expected(
    spec: AssertionSpec,
    resolver: Callable[[str], Any] | None,
) -> tuple[bool, Any, str]:
    if spec.expected_ref:
        if resolver is None:
            return False, None, f"expected_ref 无法解析: {spec.expected_ref}"
        try:
            return True, resolver(spec.expected_ref), ""
        except Exception as exc:
            return False, None, f"expected_ref 解析失败: {type(exc).__name__}: {exc}"
    return True, spec.expected, ""


def _evaluate_once(
    spec: AssertionSpec,
    actuals: Mapping[str, Any],
    *,
    expected_resolver: Callable[[str], Any] | None = None,
) -> AssertionOutcome:
    started = time.monotonic()
    expected: Any = spec.expected

    def outcome(status: AssertionStatus, actual: Any = None, error: str = "") -> AssertionOutcome:
        return AssertionOutcome(
            assertion_key=spec.assertion_key,
            schema_version=spec.schema_version,
            oracle_layer=spec.oracle_layer,
            oracle_ref=spec.oracle_ref,
            type=spec.type,
            status=status,  # type: ignore[arg-type]
            expected=expected,
            actual=actual,
            actual_source=spec.actual_source,
            severity=spec.severity,
            timeout_ms=spec.timeout_ms,
            duration_ms=int((time.monotonic() - started) * 1000),
            error=error,
        )

    if spec.oracle_layer != "REQ" and not spec.oracle_ref:
        return outcome(ERROR, error="STD/PATTERN 断言缺少 oracle_ref")
    if spec.oracle_layer == "REQ" and not spec.oracle_ref:
        return outcome(ERROR, error="REQ 断言缺少 oracle_ref（Contract/AC 引用）")

    ok, expected, err = _resolve_expected(spec, expected_resolver)
    if not ok:
        return outcome(ERROR, error=err)

    driver_status = str(actuals.get("driver_status") or "SUCCEEDED")
    if driver_status in {"BLOCKED"}:
        return outcome(BLOCKED, error="Driver BLOCKED，断言未执行")
    if driver_status in {"ERROR"}:
        return outcome(NOT_EVALUATED, error="Driver ERROR，断言未执行")

    assertion_type = spec.type
    try:
        if assertion_type == "http_status":
            actual = actuals.get("status_code")
            if actual is None:
                return outcome(NOT_EVALUATED, actual=None, error="无 HTTP status")
            if spec.operator in {"exists", "not_exists", "is_null", "not_null"}:
                passed = _compare(actual, expected, spec.operator)
            else:
                passed = _compare(actual, expected, spec.operator)
            return outcome(PASS if passed else FAIL, actual)
        if assertion_type == "jsonpath":
            if not spec.path:
                raise AssertionConfigError("jsonpath 断言缺少 path")
            found, actual = _json_path_actual(actuals.get("json"), spec.path)
            if not found:
                if spec.operator in {"not_exists", "is_null"}:
                    return outcome(PASS, None)
                return outcome(FAIL, None)
            if expected is None and spec.operator in {"eq", "equals", "=="}:
                passed = actual not in (None, "", [], {})
            else:
                passed = _compare(actual, expected, spec.operator)
            return outcome(PASS if passed else FAIL, actual)
        if assertion_type == "json_schema":
            schema = spec.schema_ or expected
            if not isinstance(schema, Mapping):
                raise AssertionConfigError("json_schema 断言缺少 schema")
            passed, message = _validate_json_schema(actuals.get("json"), schema)
            return outcome(PASS if passed else FAIL, actuals.get("json"), error=message)
        if assertion_type in {"text_contains", "text_equals"}:
            actual = actuals.get("body_text") or ""
            if spec.selector:
                locator = (actuals.get("locators") or {}).get(spec.selector) or {}
                actual = locator.get("text") or ""
            if assertion_type == "text_contains":
                passed = str(expected) in actual
            else:
                passed = actual == str(expected)
            return outcome(PASS if passed else FAIL, actual)
        if assertion_type == "locator_visible":
            locator = (actuals.get("locators") or {}).get(spec.selector or spec.path or "")
            if locator is None:
                return outcome(NOT_EVALUATED, error="无 locator 实际值")
            actual = bool(locator.get("visible"))
            return outcome(PASS if actual == bool(expected) else FAIL, actual)
        if assertion_type == "locator_count":
            locator = (actuals.get("locators") or {}).get(spec.selector or spec.path or "")
            if locator is None:
                return outcome(NOT_EVALUATED, error="无 locator 实际值")
            actual = int(locator.get("count") or 0)
            passed = _compare(actual, expected, spec.operator)
            return outcome(PASS if passed else FAIL, actual)
        if assertion_type in {"url_equals", "url_contains"}:
            actual = str(actuals.get("url") or "")
            if assertion_type == "url_equals":
                passed = actual == str(expected)
            else:
                passed = str(expected) in actual
            return outcome(PASS if passed else FAIL, actual)
        if assertion_type in {"db_value_eq", "db_row_exists", "db_row_count"}:
            db = actuals.get("db") or {}
            if not isinstance(db, Mapping) or not db:
                return outcome(NOT_EVALUATED, error="无 DB 实际值")
            if assertion_type == "db_row_exists":
                actual = int(db.get("row_count") or 0)
                passed = (actual > 0) == bool(expected if expected is not None else True)
                return outcome(PASS if passed else FAIL, actual)
            if assertion_type == "db_row_count":
                actual = int(db.get("row_count") or 0)
                passed = _compare(actual, expected, spec.operator)
                return outcome(PASS if passed else FAIL, actual)
            path = spec.path or "$.rows[0].value"
            found, actual = _json_path_actual(db, path)
            if not found:
                return outcome(FAIL, None)
            passed = _compare(actual, expected, spec.operator)
            return outcome(PASS if passed else FAIL, actual)
        if assertion_type == "event_received":
            events = actuals.get("events") or []
            actual = str(expected) in {str(item) for item in events}
            return outcome(PASS if actual else FAIL, events)
        if assertion_type == "eventually":
            inner_raw = (
                (spec.model_extra or {}).get("assertion")
                or (spec.model_extra or {}).get("inner")
                or {}
            )
            if not isinstance(inner_raw, Mapping) or not inner_raw:
                raise AssertionConfigError("eventually 缺少 inner assertion")
            inner = normalize_assertion(inner_raw, 0)
            if spec.timeout_ms <= 0:
                raise AssertionConfigError("eventually 必须声明 timeout_ms")
            deadline = started + spec.timeout_ms / 1000
            last: AssertionOutcome | None = None
            while True:
                last = _evaluate_once(inner, actuals, expected_resolver=expected_resolver)
                if last.status == PASS or time.monotonic() >= deadline:
                    break
                time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))
            return outcome(
                last.status if last else ERROR,
                last.actual if last else None,
                error=last.error if last else "eventually 无结果",
            )
        raise AssertionConfigError(f"未识别的断言类型: {assertion_type!r}")
    except AssertionConfigError as exc:
        return outcome(ERROR, error=str(exc))
    except Exception as exc:
        return outcome(ERROR, error=f"{type(exc).__name__}: {exc}")


def evaluate_assertions(
    specs: Iterable[AssertionSpec],
    actuals: Mapping[str, Any],
    *,
    expected_resolver: Callable[[str], Any] | None = None,
) -> list[AssertionOutcome]:
    return [
        _evaluate_once(spec, actuals, expected_resolver=expected_resolver)
        for spec in specs
    ]


def summarize(outcomes: Iterable[AssertionOutcome]) -> str:
    statuses = [outcome.status for outcome in outcomes]
    if not statuses:
        return NOT_EVALUATED
    if FAIL in statuses:
        return FAIL
    if ERROR in statuses:
        return ERROR
    if all(status == PASS for status in statuses):
        return PASS
    if any(status == BLOCKED for status in statuses):
        return BLOCKED
    return BLOCKED


def persist_outcomes(
    db: Session,
    attempt: StepAttempt,
    outcomes: Iterable[AssertionOutcome],
    *,
    known_secrets: Iterable[str] = (),
) -> list[RunAssertionResult]:
    """落库；同一 attempt 的同一 assertion_key 幂等更新。"""
    secrets = [str(value) for value in known_secrets if value]
    rows: list[RunAssertionResult] = []
    for outcome in outcomes:
        expected = redact(outcome.expected, known_secrets=secrets)
        actual = redact(outcome.actual, known_secrets=secrets)
        diff = redact(outcome.diff, known_secrets=secrets)
        row = db.scalar(
            select(RunAssertionResult).where(
                RunAssertionResult.step_attempt_id == attempt.id,
                RunAssertionResult.assertion_key == outcome.assertion_key,
            )
        )
        if row is None:
            row = RunAssertionResult(
                step_attempt_id=attempt.id,
                assertion_key=outcome.assertion_key,
                assertion_type=outcome.type,
            )
            db.add(row)
        row.schema_version = outcome.schema_version
        row.assertion_type = outcome.type
        row.oracle_layer = outcome.oracle_layer
        row.oracle_ref = outcome.oracle_ref
        row.rule_id = outcome.oracle_ref[:40] or None
        row.status = outcome.status
        row.expected_json = expected
        row.actual_json = actual
        row.diff_json = diff
        row.actual_source = outcome.actual_source
        row.severity = outcome.severity
        row.timeout_ms = outcome.timeout_ms
        row.duration_ms = outcome.duration_ms
        row.error_message = str(outcome.error or "")[:500]
        row.artifact_refs_json = list(outcome.artifact_refs)
        row.evidence_refs_json = list(outcome.artifact_refs)
        row.evaluated_by = "deterministic"
        rows.append(row)
    db.flush()
    return rows


def evaluate_and_persist(
    db: Session,
    *,
    node: NodeRun,
    attempt: StepAttempt,
    result: DriverResult,
    declared: Iterable[Mapping[str, Any]] | None = None,
    known_secrets: Iterable[str] = (),
    expected_resolver: Callable[[str], Any] | None = None,
) -> tuple[str, list[AssertionOutcome]]:
    """评估节点断言并落库；返回 (summary status, outcomes)。"""
    raw = list(declared if declared is not None else (node.assertions_json or []))
    try:
        specs = normalize_assertions(raw)
    except AssertionConfigError:
        raise
    actuals = build_actuals(result)
    if result.status == "BLOCKED":
        outcomes = [
            AssertionOutcome(
                assertion_key=spec.assertion_key,
                oracle_layer=spec.oracle_layer,
                oracle_ref=spec.oracle_ref,
                type=spec.type,
                status=BLOCKED,
                expected=spec.expected,
                severity=spec.severity,
                timeout_ms=spec.timeout_ms,
                error="Driver BLOCKED",
            )
            for spec in specs
        ]
    elif result.status == "ERROR":
        outcomes = [
            AssertionOutcome(
                assertion_key=spec.assertion_key,
                oracle_layer=spec.oracle_layer,
                oracle_ref=spec.oracle_ref,
                type=spec.type,
                status=NOT_EVALUATED,
                expected=spec.expected,
                severity=spec.severity,
                timeout_ms=spec.timeout_ms,
                error="Driver ERROR",
            )
            for spec in specs
        ]
    elif result.data.get("probe_only"):
        # FIX-004：probe 只证明可操作性，不能触发业务断言 PASS。
        outcomes = [
            AssertionOutcome(
                assertion_key=spec.assertion_key,
                oracle_layer=spec.oracle_layer,
                oracle_ref=spec.oracle_ref,
                type=spec.type,
                status=NOT_EVALUATED,
                expected=spec.expected,
                severity=spec.severity,
                timeout_ms=spec.timeout_ms,
                error="probe_actionability 不产生业务 PASS",
            )
            for spec in specs
        ]
    else:
        outcomes = evaluate_assertions(
            specs, actuals, expected_resolver=expected_resolver
        )
    persist_outcomes(db, attempt, outcomes, known_secrets=known_secrets)
    return summarize(outcomes), outcomes
