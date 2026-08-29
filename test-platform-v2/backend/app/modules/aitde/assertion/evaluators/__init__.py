"""Deterministic assertion evaluators (V31-007).

An operator takes (expected, actual) and returns (bool, reason_code). No LLM is
involved; an unsupported operator yields an ERROR result (never a PASS).
"""
from __future__ import annotations

import re
from typing import Any


def _norm(v: Any) -> Any:
    return v


def eq(expected: Any, actual: Any) -> tuple[bool, str]:
    return _norm(actual) == _norm(expected), "eq"


def ne(expected: Any, actual: Any) -> tuple[bool, str]:
    return _norm(actual) != _norm(expected), "ne"


def contains(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return expected in actual, "contains"  # type: ignore[operator]
    except TypeError:
        return False, "contains_typo"


def not_contains(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return expected not in actual, "not_contains"  # type: ignore[operator]
    except TypeError:
        return False, "not_contains_typo"


def matches(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return re.search(str(expected), str(actual)) is not None, "matches"
    except re.error:
        return False, "matches_bad_regex"


def gt(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return float(actual) > float(expected), "gt"  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return False, "gt_non_numeric"


def gte(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return float(actual) >= float(expected), "gte"  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return False, "gte_non_numeric"


def lt(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return float(actual) < float(expected), "lt"  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return False, "lt_non_numeric"


def lte(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return float(actual) <= float(expected), "lte"  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return False, "lte_non_numeric"


def exists(expected: Any, actual: Any) -> tuple[bool, str]:
    return actual is not None and actual != "", "exists"


def not_exists(expected: Any, actual: Any) -> tuple[bool, str]:
    return actual is None or actual == "", "not_exists"


def in_list(expected: Any, actual: Any) -> tuple[bool, str]:
    try:
        return actual in list(expected), "in_list"
    except TypeError:
        return False, "in_list_typo"


OPERATORS: dict[str, Any] = {
    "eq": eq,
    "ne": ne,
    "contains": contains,
    "not_contains": not_contains,
    "matches": matches,
    "gt": gt,
    "gte": gte,
    "lt": lt,
    "lte": lte,
    "exists": exists,
    "not_exists": not_exists,
    "in_list": in_list,
}


def evaluate(operator: str, expected: Any, actual: Any) -> tuple[bool, str]:
    fn = OPERATORS.get(operator)
    if fn is None:
        raise ValueError(f"unsupported_operator:{operator}")
    return fn(expected, actual)
