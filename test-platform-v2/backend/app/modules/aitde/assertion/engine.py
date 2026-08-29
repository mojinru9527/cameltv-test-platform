"""AssertionEngine (V31-007).

Consumes a ``TestOracle`` and an observation (actual value pulled from evidence /
an adapter's output) and produces an ``AssertionResult`` deterministically. It
never calls an LLM and never grants PASS on a NOT_EVALUATED oracle.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.modules.aitde.assertion.evaluators import evaluate
from app.modules.aitde.common.enums import AssertionResult as AssertionResultEnum
from app.modules.aitde.execution import repository


def _json_or_str(value: str) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (ValueError, json.JSONDecodeError):
        return value


class AssertionEngine:
    def evaluate(
        self, oracle_operator: str, expected_raw: str, actual: Any
    ) -> dict[str, Any]:
        """Return the assertion outcome dict for one oracle vs one observation."""
        expected = _json_or_str(expected_raw)

        # Missing observation -> NOT_EVALUATED (never a pass).
        if actual is None:
            return {
                "result": AssertionResultEnum.NOT_EVALUATED.value,
                "reason_code": "observation_missing",
                "expected_json": expected_raw,
                "actual_json": json.dumps(None),
            }

        try:
            ok, reason = evaluate(oracle_operator, expected, actual)
        except ValueError:
            return {
                "result": AssertionResultEnum.ERROR.value,
                "reason_code": f"unsupported_operator:{oracle_operator}",
                "expected_json": expected_raw,
                "actual_json": json.dumps(actual, ensure_ascii=False),
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "result": AssertionResultEnum.ERROR.value,
                "reason_code": f"eval_error:{exc}",
                "expected_json": expected_raw,
                "actual_json": json.dumps(actual, ensure_ascii=False),
            }

        result = (
            AssertionResultEnum.PASS.value if ok else AssertionResultEnum.FAIL.value
        )
        return {
            "result": result,
            "reason_code": reason,
            "expected_json": expected_raw,
            "actual_json": json.dumps(actual, ensure_ascii=False),
        }


def evaluate_and_persist(
    db: Session,
    *,
    run_id: int,
    oracle_id: int,
    oracle_snapshot: dict[str, Any],
    actual: Any,
    step_id: int | None = None,
    evidence_refs: list[int] | None = None,
    engine: AssertionEngine | None = None,
) -> dict[str, Any]:
    """Evaluate one oracle against an observation and persist an AssertionResult."""
    eng = engine or AssertionEngine()
    operator = oracle_snapshot.get("operator") or "eq"
    expected_raw = oracle_snapshot.get("expected_value_json") or "{}"
    outcome = eng.evaluate(operator, expected_raw, actual)

    row = repository.add_assertion(
        db,
        {
            "run_id": run_id,
            "step_id": step_id,
            "oracle_id": oracle_id,
            "oracle_snapshot_json": json.dumps(
                oracle_snapshot, ensure_ascii=False, sort_keys=True
            ),
            "expected_json": outcome["expected_json"],
            "actual_json": outcome["actual_json"],
            "result": outcome["result"],
            "reason_code": outcome["reason_code"],
            "evidence_refs_json": json.dumps(evidence_refs or []),
            "evaluated_at": datetime.utcnow(),
        },
    )
    return {
        "id": row.id,
        "result": row.result,
        "reason_code": row.reason_code,
    }
