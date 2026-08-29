"""DataOracleEvaluator (V32-013).

Connects a DB oracle to the V3.1 AssertionEngine and guarantees a DB *read*
failure is never misclassified as a business failure. DB/runtime problems map to
ASSERTION_ERROR; only a deterministic assertion result can produce PASS/FAIL.
"""
from __future__ import annotations

from typing import Any

from app.modules.aitde.assertion.engine import AssertionEngine
from app.modules.aitde.common.enums import AssertionResult


def classify_db_read_failure(exc: Exception) -> str:
    """DB read problems are infrastructure, never a business failure."""
    return "ASSERTION_ERROR"


class DataOracleEvaluator:
    def __init__(self, engine: AssertionEngine | None = None):
        self._engine = engine or AssertionEngine()

    def evaluate(self, oracle_snapshot: dict[str, Any], actual: Any) -> dict[str, Any]:
        operator = oracle_snapshot.get("operator") or "eq"
        expected_raw = oracle_snapshot.get("expected_value_json") or "{}"
        outcome = self._engine.evaluate(operator, expected_raw, actual)
        outcome["category"] = "db_oracle"
        return outcome

    @staticmethod
    def is_not_evaluated(outcome: dict[str, Any]) -> bool:
        return outcome.get("result") == AssertionResult.NOT_EVALUATED.value
