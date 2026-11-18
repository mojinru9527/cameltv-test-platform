"""AUD-007：Assertion Operator Registry（有类型的算子 + 版本）。

v1.5 §01 AUD-007 第 2 条：每个 operator 必须有类型签名、空值语义、错误语义、
超时行为和版本。算子只做**确定性**判定，不执行任意代码。
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.aiqe.assertions.observation import InvalidJsonPath, Observation, resolve_json_path

OPERATOR_VERSION = "1.0.0"

#: 断言来源 → Observation 读取方式。
SOURCES: frozenset[str] = frozenset(
    {
        "http_status",
        "http_header",
        "http_body",
        "http_text",
        "json",
        "response",
        "dom",
        "db_query",
        "db",
        "event",
        "timing",
    }
)


class OperatorError(ValueError):
    """算子自身无法评估（进入 ERROR，不伪装成产品 FAIL）。"""


@dataclass(frozen=True)
class OperatorResult:
    passed: bool
    actual: Any
    found: bool = True
    detail: dict[str, Any] = field(default_factory=dict)


class AssertionLike:
    """断言配置的最小协议（dict 包装，供算子读取 path/expected）。"""

    def __init__(self, spec: Mapping[str, Any]) -> None:
        self._spec = dict(spec or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._spec.get(key, default)

    @property
    def path(self) -> str:
        return str(self._spec.get("path") or "")

    @property
    def expected(self) -> Any:
        return self._spec.get("expected")

    @property
    def source(self) -> str:
        return str(self._spec.get("source") or "")


@dataclass(frozen=True)
class OperatorSpec:
    key: str
    version: str
    description: str
    fn: Callable[[Any, AssertionLike], OperatorResult]


def read_source(obs: Observation, spec: AssertionLike) -> tuple[bool, Any]:
    """按 ``source`` 读取实际值；返回 ``(found, value)``。"""
    source = spec.source or "http_body"
    path = spec.path
    if source == "http_status":
        return obs.status_code is not None, obs.status_code
    if source == "http_header":
        if not path:
            raise OperatorError("header 断言必须提供 path（Header 名）")
        return obs.header(path)
    if source == "http_text":
        if path:
            found, value = _safe_path(obs.text, path)
            return found, value
        return True, obs.text
    if source in {"http_body", "json", "response"}:
        if not path:
            return True, obs.body
        return _safe_path(obs.body, path)
    if source == "dom":
        if obs.dom is None:
            return False, None
        if not path:
            return True, obs.dom
        return _safe_path(obs.dom, path)
    if source in {"db_query", "db"}:
        if not path:
            return True, list(obs.db_rows)
        return _safe_path(list(obs.db_rows), path)
    if source == "event":
        if not path:
            return True, list(obs.events)
        return _safe_path(list(obs.events), path)
    if source == "timing":
        if not path:
            return True, dict(obs.timings)
        return (path in obs.timings), obs.timings.get(path)
    raise OperatorError(f"未知断言来源: {source!r}")


def _safe_path(data: Any, path: str) -> tuple[bool, Any]:
    try:
        return resolve_json_path(data, path)
    except InvalidJsonPath as exc:
        raise OperatorError(str(exc)) from exc


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _op_equals(value: Any, spec: AssertionLike) -> OperatorResult:
    expected = spec.expected
    passed = _normalize_scalar(value) == _normalize_scalar(expected)
    return OperatorResult(passed=passed, actual=value, detail={"expected": expected})


def _op_not_equals(value: Any, spec: AssertionLike) -> OperatorResult:
    expected = spec.expected
    passed = _normalize_scalar(value) != _normalize_scalar(expected)
    return OperatorResult(passed=passed, actual=value, detail={"expected": expected})


def _op_contains(value: Any, spec: AssertionLike) -> OperatorResult:
    expected = str(spec.expected)
    if isinstance(value, str):
        passed = expected in value
    elif isinstance(value, (list, tuple, set)):
        passed = expected in {str(item) for item in value} or expected in value
    elif isinstance(value, Mapping):
        passed = expected in {str(key) for key in value}
    else:
        passed = expected in str(value)
    return OperatorResult(passed=passed, actual=value, detail={"expected_contains": expected})


def _op_not_contains(value: Any, spec: AssertionLike) -> OperatorResult:
    inner = _op_contains(value, spec)
    return OperatorResult(passed=not inner.passed, actual=value, detail=inner.detail)


def _op_exists(value: Any, spec: AssertionLike) -> OperatorResult:
    expected = spec.expected if spec.expected is not None else True
    passed = value is not None if expected else value is None
    return OperatorResult(passed=passed, actual=value, detail={"expected_exists": bool(expected)})


def _op_not_exists(value: Any, spec: AssertionLike) -> OperatorResult:
    return OperatorResult(passed=value is None, actual=value)


def _op_regex(value: Any, spec: AssertionLike) -> OperatorResult:
    pattern = str(spec.expected or "")
    if not pattern:
        raise OperatorError("regex 断言必须提供 expected（正则）")
    try:
        matched = re.search(pattern, str(value)) is not None
    except re.error as exc:
        raise OperatorError(f"非法正则: {exc}") from exc
    return OperatorResult(passed=matched, actual=value, detail={"pattern": pattern})


def _op_in(value: Any, spec: AssertionLike) -> OperatorResult:
    expected = spec.expected
    if not isinstance(expected, (list, tuple, set)):
        raise OperatorError("in 断言的 expected 必须是数组")
    passed = _normalize_scalar(value) in {_normalize_scalar(item) for item in expected}
    return OperatorResult(passed=passed, actual=value, detail={"expected_in": list(expected)})


def _op_gte(value: Any, spec: AssertionLike) -> OperatorResult:
    try:
        passed = float(value) >= float(spec.expected)
    except (TypeError, ValueError) as exc:
        raise OperatorError("gte 断言需要可比较的数值") from exc
    return OperatorResult(passed=passed, actual=value, detail={"min": spec.expected})


def _op_lte(value: Any, spec: AssertionLike) -> OperatorResult:
    try:
        passed = float(value) <= float(spec.expected)
    except (TypeError, ValueError) as exc:
        raise OperatorError("lte 断言需要可比较的数值") from exc
    return OperatorResult(passed=passed, actual=value, detail={"max": spec.expected})


def _op_json_schema(value: Any, spec: AssertionLike) -> OperatorResult:
    """轻量 JSON Schema 子集：type/required/properties/items（无第三方依赖）。"""
    schema = spec.expected
    if not isinstance(schema, Mapping):
        raise OperatorError("json_schema 断言的 expected 必须是 schema 对象")
    errors: list[str] = []

    def _check(node: Any, node_schema: Mapping[str, Any], where: str) -> None:
        expected_type = node_schema.get("type")
        if expected_type:
            mapping: dict[str, type | tuple[type, ...]] = {
                "object": dict,
                "array": list,
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "null": type(None),
            }
            python_type = mapping.get(str(expected_type))
            if python_type is None:
                errors.append(f"{where}: 不支持的 type {expected_type}")
                return
            if expected_type in {"integer", "number"} and isinstance(node, bool):
                errors.append(f"{where}: 期望 {expected_type}，实际 bool")
                return
            if not isinstance(node, python_type):
                errors.append(f"{where}: 期望 {expected_type}，实际 {type(node).__name__}")
                return
        if isinstance(node, Mapping):
            for key in node_schema.get("required") or []:
                if key not in node:
                    errors.append(f"{where}/{key}: 缺少必需字段")
            for key, sub_schema in (node_schema.get("properties") or {}).items():
                if key in node and isinstance(sub_schema, Mapping):
                    _check(node[key], sub_schema, f"{where}/{key}")
        if isinstance(node, list) and isinstance(node_schema.get("items"), Mapping):
            for index, item in enumerate(node):
                _check(item, node_schema["items"], f"{where}[{index}]")

    _check(value, schema, "$")
    return OperatorResult(
        passed=not errors,
        actual=value,
        detail={"errors": errors[:10], "schema": schema} if errors else {"schema": schema},
    )


REGISTRY: dict[str, OperatorSpec] = {
    "equals": OperatorSpec("equals", OPERATOR_VERSION, "严格相等（标量归一化）", _op_equals),
    "eq": OperatorSpec("eq", OPERATOR_VERSION, "equals 别名", _op_equals),
    "not_equals": OperatorSpec("not_equals", OPERATOR_VERSION, "不相等", _op_not_equals),
    "ne": OperatorSpec("ne", OPERATOR_VERSION, "not_equals 别名", _op_not_equals),
    "contains": OperatorSpec("contains", OPERATOR_VERSION, "字符串/数组/对象包含", _op_contains),
    "not_contains": OperatorSpec(
        "not_contains", OPERATOR_VERSION, "不包含", _op_not_contains
    ),
    "exists": OperatorSpec("exists", OPERATOR_VERSION, "字段存在且非 None", _op_exists),
    "not_exists": OperatorSpec("not_exists", OPERATOR_VERSION, "字段不存在", _op_not_exists),
    "regex": OperatorSpec("regex", OPERATOR_VERSION, "正则匹配（re.search）", _op_regex),
    "in": OperatorSpec("in", OPERATOR_VERSION, "值属于数组", _op_in),
    "gte": OperatorSpec("gte", OPERATOR_VERSION, "数值 >= 期望", _op_gte),
    "lte": OperatorSpec("lte", OPERATOR_VERSION, "数值 <= 期望", _op_lte),
    "json_schema": OperatorSpec(
        "json_schema", OPERATOR_VERSION, "JSON Schema 子集校验", _op_json_schema
    ),
}


def resolve_operator(key: str) -> OperatorSpec:
    spec = REGISTRY.get(str(key or "").strip().lower())
    if spec is None:
        raise OperatorError(f"未注册的算子: {key!r}")
    return spec


def known_operators() -> frozenset[str]:
    return frozenset(REGISTRY)


def evaluate_operator(spec: Mapping[str, Any], observation: Observation) -> OperatorResult:
    assertion = AssertionLike(spec)
    operator = resolve_operator(assertion.get("operator") or "equals")
    found, value = read_source(observation, assertion)
    if not found:
        return OperatorResult(
            passed=False,
            actual=None,
            found=False,
            detail={
                "reason": "SOURCE_VALUE_MISSING",
                "source": assertion.source or "http_body",
                "path": assertion.path,
                "raw": json.dumps(observation.meta, default=str)[:200] if observation.meta else "",
            },
        )
    result = operator.fn(value, assertion)
    return OperatorResult(
        passed=result.passed,
        actual=result.actual,
        found=True,
        detail={"operator": operator.key, "operator_version": operator.version, **result.detail},
    )


__all__ = [
    "OPERATOR_VERSION",
    "REGISTRY",
    "SOURCES",
    "AssertionLike",
    "OperatorError",
    "OperatorResult",
    "OperatorSpec",
    "evaluate_operator",
    "known_operators",
    "read_source",
    "resolve_operator",
]
