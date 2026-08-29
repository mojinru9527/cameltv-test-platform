"""AssertionEngine evaluator tests (V31-007). No LLM may be involved."""
from __future__ import annotations

from app.modules.aitde.assertion.engine import AssertionEngine
from app.modules.aitde.common.enums import AssertionResult as AssertionResultEnum


def test_eq_pass_and_fail():
    eng = AssertionEngine()
    ok = eng.evaluate("eq", "200", 200)
    assert ok["result"] == AssertionResultEnum.PASS.value
    bad = eng.evaluate("eq", "200", 500)
    assert bad["result"] == AssertionResultEnum.FAIL.value


def test_contains():
    eng = AssertionEngine()
    res = eng.evaluate("contains", '"ok"', "response body ok")
    assert res["result"] == AssertionResultEnum.PASS.value


def test_missing_observation_is_not_evaluated():
    eng = AssertionEngine()
    res = eng.evaluate("eq", '"200"', None)
    assert res["result"] == AssertionResultEnum.NOT_EVALUATED.value


def test_unsupported_operator_is_error():
    eng = AssertionEngine()
    res = eng.evaluate("magic_operator", '"x"', "x")
    assert res["result"] == AssertionResultEnum.ERROR.value


def test_gt_non_numeric_is_error_safe():
    eng = AssertionEngine()
    # numeric comparison with non-numeric actual must not crash or pass
    res = eng.evaluate("gt", "5", "abc")
    assert res["result"] == AssertionResultEnum.FAIL.value
