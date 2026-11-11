"""M3 / TA-024.2：Noise Hint Agent 单测（广告抖动样本 + 安全规则）。"""
from __future__ import annotations

import json

import pytest

from app.aiqe.agents.base import AgentSchemaError
from app.aiqe.agents.noise_hint_agent import NoiseHintAgent


def hint(**overrides) -> dict:
    data = {
        "hint": "广告浮层遮挡入口",
        "suspected_factor": "AD_JITTER",
        "evidence_refs": ["artifact:screenshot-1", "event:104"],
    }
    data.update(overrides)
    return data


def payload(hints=None, **overrides) -> dict:
    data = {
        "hints": hints if hints is not None else [hint()],
        "human_review_required": True,
        "auto_close_defect": False,
    }
    data.update(overrides)
    return data


def agent_returning(data: dict) -> NoiseHintAgent:
    return NoiseHintAgent(lambda system, user: json.dumps(data, ensure_ascii=False))


def test_ad_jitter_sample_with_evidence():
    result = agent_returning(payload()).analyze({"failure": {"test": "直播入口"}})
    assert result["hints"][0]["suspected_factor"] == "AD_JITTER"
    assert result["hints"][0]["evidence_refs"] == ["artifact:screenshot-1", "event:104"]
    assert result["auto_close_defect"] is False and result["human_review_required"] is True


def test_at_most_three_hints():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload(hints=[hint(), hint(), hint(), hint()])).analyze({"x": 1})


def test_empty_evidence_rejected():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload(hints=[hint(evidence_refs=[])])).analyze({"x": 1})


def test_invalid_evidence_prefix_rejected():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload(hints=[hint(evidence_refs=["http://evil"])])).analyze({"x": 1})


def test_auto_close_rejected():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload(auto_close_defect=True)).analyze({"x": 1})


def test_human_review_required():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload(human_review_required=False)).analyze({"x": 1})


def test_unknown_factor_allowed():
    unknown = hint(suspected_factor="UNKNOWN", hint="证据不足，疑似环境抖动")
    result = agent_returning(payload(hints=[unknown])).analyze({"x": 1})
    assert result["hints"][0]["suspected_factor"] == "UNKNOWN"


def test_zero_hints_rejected():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload(hints=[])).analyze({"x": 1})
