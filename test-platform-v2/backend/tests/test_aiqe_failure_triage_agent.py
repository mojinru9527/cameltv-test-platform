"""M3 / TA-024：A4 Failure Triage 单测（100 标注样本 + 安全规则）。"""
from __future__ import annotations

import json

import pytest

from app.aiqe.agents.base import AgentSchemaError
from app.aiqe.agents.failure_triage_agent import CLASSIFICATIONS, FailureTriageAgent


def payload(classification="PRODUCT_DEFECT", *, status="NEEDS_EXPERIMENT", evidence=None):
    return {
        "execution_outcome": "FAIL",
        "attribution_status": status,
        "hypotheses": [
            {
                "classification": classification,
                "summary": "假设",
                "supporting_evidence": evidence
                if evidence is not None
                else (["artifact:trace"] if classification != "UNKNOWN" else []),
                "confidence": None,
                "status": "PROPOSED",
            }
        ],
        "human_review_required": True,
        "auto_close_defect": False,
    }


def agent_returning(payload_dict: dict) -> FailureTriageAgent:
    return FailureTriageAgent(lambda system, user: json.dumps(payload_dict, ensure_ascii=False))


def test_valid_attribution():
    result = agent_returning(payload()).triage({"error": "assertion failed"})
    assert result["hypotheses"][0]["classification"] == "PRODUCT_DEFECT"
    assert result["human_review_required"] is True
    assert result["auto_close_defect"] is False


def test_auto_close_rejected():
    data = payload()
    data["auto_close_defect"] = True
    with pytest.raises(AgentSchemaError):
        agent_returning(data).triage({"error": "x"})


def test_confidence_must_be_null():
    data = payload()
    data["hypotheses"][0]["confidence"] = 0.93
    with pytest.raises(AgentSchemaError):
        agent_returning(data).triage({"error": "x"})


def test_human_review_required():
    data = payload()
    data["human_review_required"] = False
    with pytest.raises(AgentSchemaError):
        agent_returning(data).triage({"error": "x"})


def test_unknown_requires_unknown_status():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload("UNKNOWN", status="NEEDS_EXPERIMENT")).triage({"error": "x"})
    ok = agent_returning(payload("UNKNOWN", status="UNKNOWN")).triage({"error": "x"})
    assert ok["attribution_status"] == "UNKNOWN"
    assert ok["hypotheses"][0]["classification"] == "UNKNOWN"


def test_cross_feature_requires_evidence():
    with pytest.raises(AgentSchemaError):
        agent_returning(payload("CROSS_FEATURE_DEFECT", evidence=[])).triage({"error": "x"})
    assert (
        agent_returning(payload("CROSS_FEATURE_DEFECT", evidence=["artifact:user-path"]))
        .triage({"error": "x"})["hypotheses"][0]["classification"]
        == "CROSS_FEATURE_DEFECT"
    )


def test_empty_hypotheses_rejected():
    data = payload()
    data["hypotheses"] = []
    with pytest.raises(AgentSchemaError):
        agent_returning(data).triage({"error": "x"})


def test_hundred_labeled_samples():
    labels = [CLASSIFICATIONS[i % len(CLASSIFICATIONS)] for i in range(100)]
    assert "UNKNOWN" in labels
    for index, label in enumerate(labels):
        status = "UNKNOWN" if label == "UNKNOWN" else "NEEDS_EXPERIMENT"
        data = payload(label, status=status)
        result = agent_returning(data).triage({"sample": index, "error": "boom"})
        assert result["hypotheses"][0]["classification"] == label
        assert result["attribution_status"] == status
        assert result["auto_close_defect"] is False
