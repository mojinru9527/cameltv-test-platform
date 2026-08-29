"""V33-005 UI Oracle evaluator tests."""
from __future__ import annotations

from app.modules.aitde.browser.ui_oracle import UiOracleEvaluator
from app.modules.aitde.common.enums import AssertionResult


def _oracle(operator, expected):
    return {"operator": operator, "expected_value_json": expected}


def test_visible_pass_fail():
    ev = UiOracleEvaluator()
    assert ev.evaluate(_oracle("visible", '{"visible": true}'), {"visible": True})["result"] == AssertionResult.PASS.value
    assert ev.evaluate(_oracle("visible", '{"visible": true}'), {"visible": False})["result"] == AssertionResult.FAIL.value


def test_text_pass_fail():
    ev = UiOracleEvaluator()
    assert ev.evaluate(_oracle("text", '{"text": "已续费"}'), {"text": "已续费"})["result"] == AssertionResult.PASS.value
    assert ev.evaluate(_oracle("text", '{"text": "已续费"}'), {"text": "未续费"})["result"] == AssertionResult.FAIL.value


def test_contains():
    ev = UiOracleEvaluator()
    assert ev.evaluate(_oracle("contains", '{"text": "续费"}'), {"text": "会员已续费成功"})["result"] == AssertionResult.PASS.value


def test_attribute():
    ev = UiOracleEvaluator()
    out = ev.evaluate(_oracle("attribute", '{"key": "data-testid", "value": "renew-btn"}'), {"attributes": {"data-testid": "renew-btn"}})
    assert out["result"] == AssertionResult.PASS.value


def test_state():
    ev = UiOracleEvaluator()
    out = ev.evaluate(_oracle("state", '{"key": "checked", "value": true}'), {"state": {"checked": True}})
    assert out["result"] == AssertionResult.PASS.value


def test_observation_missing_not_evaluated():
    ev = UiOracleEvaluator()
    out = ev.evaluate(_oracle("text", '{"text": "x"}'), None)
    assert out["result"] == AssertionResult.NOT_EVALUATED.value
    assert out["result"] != AssertionResult.PASS.value
