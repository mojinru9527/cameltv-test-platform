"""M3 / TA-019：A0 Requirement Agent + 编排执行记录单测。"""
from __future__ import annotations

import json

import pytest

from app.aiqe.agents.base import AgentSchemaError, AgentUnavailable
from app.aiqe.agents.orchestrator import run_agent
from app.aiqe.agents.requirement_agent import RequirementAgent
from app.aiqe.models.agent import AgentExecution


def valid_output(summary="直播发布需求") -> dict:
    return {
        "summary": summary,
        "acceptance_criteria": [
            {"id": "AC1", "text": "后台可创建直播", "source_ref": "REQ#1"},
            {"id": "AC2", "text": "前台可见直播", "source_ref": "REQ#2"},
        ],
        "risks": ["并发发布"],
    }


def llm_returning(payload: dict):
    return lambda system, user: json.dumps(payload, ensure_ascii=False)


def test_run_agent_success_records_execution(db_session):
    agent = RequirementAgent(llm_returning(valid_output()))
    output = run_agent(db_session, agent, project_id=1, input_text="需求原文")
    db_session.commit()

    assert output["summary"] == "直播发布需求"
    assert all(item["source_ref"] for item in output["acceptance_criteria"])
    row = db_session.query(AgentExecution).one()
    assert row.status == "succeeded"
    assert row.agent_key == "A0"
    assert row.output_json["acceptance_criteria"][0]["id"] == "AC1"


def test_missing_source_ref_rejected(db_session):
    payload = valid_output()
    payload["acceptance_criteria"][0]["source_ref"] = ""
    agent = RequirementAgent(llm_returning(payload))
    with pytest.raises(AgentSchemaError):
        run_agent(db_session, agent, project_id=1, input_text="需求原文")
    db_session.commit()
    row = db_session.query(AgentExecution).one()
    assert row.status == "failed"
    assert "source_ref" in row.error_text


def test_invalid_json_rejected(db_session):
    agent = RequirementAgent(lambda system, user: "not-json")
    with pytest.raises(AgentSchemaError):
        run_agent(db_session, agent, project_id=1, input_text="x")
    db_session.commit()
    assert db_session.query(AgentExecution).one().status == "failed"


def test_missing_summary_rejected_and_missing_llm_fail_closed(db_session):
    payload = valid_output()
    payload.pop("summary")
    with pytest.raises(AgentSchemaError):
        RequirementAgent(llm_returning(payload)).run("x")

    with pytest.raises(AgentUnavailable):
        RequirementAgent(None).run("x")
    with pytest.raises(AgentUnavailable):
        run_agent(db_session, RequirementAgent(None), project_id=1, input_text="x")
    db_session.commit()
    assert db_session.query(AgentExecution).one().status == "failed"


def test_fenced_json_accepted():
    agent = RequirementAgent(
        lambda system, user: "```json\n" + json.dumps(valid_output()) + "\n```"
    )
    assert agent.run("x")["summary"] == "直播发布需求"


def test_thirty_requirement_samples_all_valid():
    samples = [f"REQ-{i:03d}: 直播场景{i}发布需求" for i in range(1, 31)]
    agent = RequirementAgent(
        lambda system, user: json.dumps(
            {
                "summary": user[:40],
                "acceptance_criteria": [
                    {"id": "AC1", "text": "可创建", "source_ref": f"{user}#1"},
                    {"id": "AC2", "text": "可见", "source_ref": f"{user}#2"},
                ],
                "risks": [],
            },
            ensure_ascii=False,
        )
    )
    results = [agent.run(sample) for sample in samples]
    assert len(results) == 30
    assert all(result["acceptance_criteria"] for result in results)
    assert all(
        item["source_ref"] for result in results for item in result["acceptance_criteria"]
    )
