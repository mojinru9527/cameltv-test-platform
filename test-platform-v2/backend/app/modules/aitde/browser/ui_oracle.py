"""AITDE V3.3 UI Oracle evaluator (V33-005).

Deterministic assertions over a normalized DOM observation. Never calls an LLM —
PASS/FAIL is computed from the frozen oracle operator + observation. Missing
observation ⇒ NOT_EVALUATED (never a pass).
"""
from __future__ import annotations

import json
from typing import Any

from app.modules.aitde.common.enums import AssertionResult


class UiOracleEvaluator:
    def evaluate(
        self, oracle_snapshot: dict[str, Any], actual: dict[str, Any] | None
    ) -> dict[str, Any]:
        operator = oracle_snapshot.get("operator") or "text"
        expected_raw = oracle_snapshot.get("expected_value_json") or "{}"
        try:
            expected = json.loads(expected_raw)
        except (ValueError, TypeError):
            expected = expected_raw

        if actual is None:
            return {"result": AssertionResult.NOT_EVALUATED.value, "reason": "observation_missing"}

        ok, reason = self._apply(operator, expected, actual)
        return {
            "result": AssertionResult.PASS.value if ok else AssertionResult.FAIL.value,
            "reason": reason,
        }

    def _apply(self, operator: str, expected: Any, actual: dict[str, Any]) -> tuple[bool, str]:
        if operator == "visible":
            want = expected.get("visible", True) if isinstance(expected, dict) else expected
            return actual.get("visible") is want, "visible"
        if operator == "text":
            want = expected.get("text", expected) if isinstance(expected, dict) else expected
            return str(actual.get("text", "")) == str(want), "text"
        if operator == "contains":
            want = expected.get("text", expected) if isinstance(expected, dict) else expected
            return str(want) in str(actual.get("text", "")), "contains"
        if operator == "attribute":
            key = (expected or {}).get("key") if isinstance(expected, dict) else None
            val = (expected or {}).get("value") if isinstance(expected, dict) else None
            attrs = actual.get("attributes") or {}
            return bool(key) and attrs.get(key) == val, "attribute"
        if operator == "state":
            key = (expected or {}).get("key") if isinstance(expected, dict) else None
            val = (expected or {}).get("value") if isinstance(expected, dict) else None
            state = actual.get("state") or {}
            return bool(key) and state.get(key) == val, "state"
        # fallback: equality on the whole observation
        return actual == expected, f"unsupported:{operator}"
