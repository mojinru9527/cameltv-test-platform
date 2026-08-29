"""DB Oracle evaluator tests (V32-013)."""
from __future__ import annotations

from app.modules.aitde.data.db_oracle import (
    DataOracleEvaluator,
    classify_db_read_failure,
)


def _oracle(operator="eq", expected='{"status": "active"}'):
    return {"operator": operator, "expected_value_json": expected}


def test_db_oracle_pass(db):
    ev = DataOracleEvaluator()
    outcome = ev.evaluate(_oracle(), {"status": "active"})
    assert outcome["result"] == "PASS"
    assert outcome["category"] == "db_oracle"


def test_db_oracle_fail(db):
    ev = DataOracleEvaluator()
    outcome = ev.evaluate(_oracle(), {"status": "expired"})
    assert outcome["result"] == "FAIL"


def test_db_oracle_missing_observation_not_evaluated(db):
    ev = DataOracleEvaluator()
    outcome = ev.evaluate(_oracle(), None)
    assert ev.is_not_evaluated(outcome) is True
    assert outcome["result"] != "PASS"


def test_db_read_exception_never_business_fail():
    # A DB read problem must never be misclassified as a business failure.
    assert classify_db_read_failure(RuntimeError("down")) == "ASSERTION_ERROR"
    assert classify_db_read_failure(RuntimeError("down")) != "BUSINESS_FAIL"
