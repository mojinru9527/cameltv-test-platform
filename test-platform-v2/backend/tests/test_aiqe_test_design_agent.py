"""M3 / TA-020：A2 Test Design / Review 单测。"""
from __future__ import annotations

import json

import pytest

from app.aiqe.agents.base import AgentSchemaError
from app.aiqe.agents.test_design_agent import TestDesignAgent


def output(decision="approve", cases=None, **extra) -> dict:
    payload = {
        "decision": decision,
        "cases": cases
        if cases is not None
        else [
            {
                "title": "创建直播",
                "priority": "P0",
                "steps": ["打开后台", "点击创建"],
                "acceptance_refs": ["AC1"],
            }
        ],
        "coverage_notes": "",
        "reject_reason": "",
        "duplicate_of": [],
    }
    payload.update(extra)
    return payload


def agent_returning(payload: dict) -> TestDesignAgent:
    return TestDesignAgent(lambda system, user: json.dumps(payload, ensure_ascii=False))


def test_approve_with_p0_acceptance_refs():
    result = agent_returning(output()).run_design({"summary": "x"})
    assert result["decision"] == "approve"
    assert result["cases"][0]["acceptance_refs"] == ["AC1"]


def test_p0_without_acceptance_refs_rejected():
    cases = [
        {"title": "创建直播", "priority": "P0", "steps": ["a"], "acceptance_refs": []}
    ]
    with pytest.raises(AgentSchemaError):
        agent_returning(output(cases=cases)).run_design({"summary": "x"})


def test_covered_requires_skip_not_duplicate():
    with pytest.raises(AgentSchemaError):
        agent_returning(output()).run_design({"summary": "x"}, coverage_sufficient=True)

    skip = output(decision="skip", cases=[], coverage_notes="已有 3 条用例覆盖")
    result = agent_returning(skip).run_design(
        {"summary": "x"}, coverage_sufficient=True
    )
    assert result["decision"] == "skip" and result["cases"] == []


def test_skip_with_cases_rejected():
    skip = output(decision="skip", coverage_notes="覆盖充分")
    with pytest.raises(AgentSchemaError):
        agent_returning(skip).run_design({"summary": "x"})


def test_reject_requires_reason_and_no_cases():
    with pytest.raises(AgentSchemaError):
        agent_returning(output(decision="reject", cases=[])).run_design({"summary": "x"})
    ok = output(decision="reject", cases=[], reject_reason="缺少验收标准")
    assert agent_returning(ok).run_design({"summary": "x"})["decision"] == "reject"


def test_invalid_schema_rejected():
    bad = output()
    bad.pop("decision")
    with pytest.raises(AgentSchemaError):
        agent_returning(bad).run_design({"summary": "x"})


def test_fifty_requirement_samples_all_valid():
    samples = [{"summary": f"需求 {i}", "acceptance_criteria": ["AC1"]} for i in range(50)]
    agent = TestDesignAgent(
        lambda system, user: json.dumps(
            output(
                cases=[
                    {
                        "title": "核心场景",
                        "priority": "P0",
                        "steps": ["step1", "step2"],
                        "acceptance_refs": ["AC1"],
                    }
                ]
            ),
            ensure_ascii=False,
        )
    )
    results = [agent.run_design(sample) for sample in samples]
    assert len(results) == 50
    assert all(r["decision"] == "approve" for r in results)
    assert all(r["cases"][0]["acceptance_refs"] for r in results)
