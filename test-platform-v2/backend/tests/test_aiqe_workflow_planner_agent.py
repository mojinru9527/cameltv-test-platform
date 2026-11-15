"""M3 / TA-021：A3 Workflow Planner 单测。"""
from __future__ import annotations

import json

import pytest

from app.aiqe.agents.base import AgentSchemaError
from app.aiqe.agents.workflow_planner_agent import (
    WorkflowNotApproved,
    WorkflowPlannerAgent,
)


def graph(deps: dict[str, list[str]], *, driver="http", scenario="SPORT-1") -> dict:
    nodes = [
        {
            "key": key,
            "driver": driver,
            "depends_on": values,
            "input": {"url": "http://example.test/health", "method": "GET"},
            "assertions": [
                {
                    "assertion_key": f"{key}_status",
                    "type": "http_status",
                    "oracle_layer": "STD",
                    "oracle_ref": "TC-A3-001",
                    "expected": 200,
                }
            ],
        }
        for key, values in deps.items()
    ]
    edges = [
        {"from": dep, "to": key}
        for key, values in deps.items()
        for dep in values
    ]
    return {
        "schema_version": "1.0",
        "scenario_key": scenario,
        "nodes": nodes,
        "edges": edges,
        "run_policy": {"max_parallel_nodes": 3, "fail_fast": False},
    }


def plan_payload(deps: dict[str, list[str]], **overrides) -> dict:
    payload = {
        "workflow": graph(deps),
        "rationale": "linear",
        "approval_required": True,
        "approval_status": "pending",
    }
    payload.update(overrides)
    return payload


def agent_returning(payload: dict, **kwargs) -> WorkflowPlannerAgent:
    return WorkflowPlannerAgent(
        lambda system, user: json.dumps(payload, ensure_ascii=False), **kwargs
    )


def test_valid_plan_is_pending():
    deps = {"a": [], "b": ["a"], "c": ["a"]}
    result = agent_returning(plan_payload(deps)).plan({"summary": "x"})
    assert result["approval_status"] == "pending"
    assert result["approval_required"] is True
    assert result["workflow"]["nodes"][1]["depends_on"] == ["a"]


def test_self_approval_rejected():
    deps = {"a": [], "b": ["a"]}
    with pytest.raises(AgentSchemaError):
        agent_returning(plan_payload(deps, approval_status="approved")).plan({"summary": "x"})


def test_cycle_rejected():
    deps = {"a": ["b"], "b": ["a"]}
    with pytest.raises(AgentSchemaError):
        agent_returning(plan_payload(deps)).plan({"summary": "x"})


def test_unknown_driver_rejected():
    deps = {"a": [], "b": ["a"]}
    # 用未知 driver 重新构造
    bad = plan_payload(deps)
    bad["workflow"]["nodes"][0]["driver"] = "quantum"
    with pytest.raises(AgentSchemaError):
        agent_returning(bad).plan({"summary": "x"})


def test_non_executable_steps_query_plan_rejected():
    bad = plan_payload({"a": []})
    bad["workflow"]["nodes"][0] = {
        "key": "a",
        "driver": "http",
        "depends_on": [],
        "steps": [{"action": "goto", "path": "/"}],
        "assertions": [{"type": "text_visible", "expected": "ok"}],
    }
    with pytest.raises(AgentSchemaError):
        agent_returning(bad).plan({"summary": "x"})


def test_dependencies_match():
    workflow = graph({"a": [], "b": ["a"], "c": ["a"]})
    assert WorkflowPlannerAgent.dependencies_match(workflow, {"b": ["a"], "c": ["a"]})
    assert not WorkflowPlannerAgent.dependencies_match(workflow, {"b": []})


def test_unapproved_cannot_execute():
    with pytest.raises(WorkflowNotApproved):
        WorkflowPlannerAgent.ensure_executable({"approval_status": "pending"})
    WorkflowPlannerAgent.ensure_executable({"approval_status": "approved"})


def test_twenty_labeled_workflows():
    labels = []
    for i in range(20):
        if i % 4 == 0:
            labels.append({"a": [], "b": ["a"], "c": ["b"]})
        elif i % 4 == 1:
            labels.append({"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]})
        elif i % 4 == 2:
            labels.append({"a": [], "b": [], "c": ["a", "b"]})
        else:
            labels.append({"a": [], "b": ["a"], "c": ["b"], "d": ["c"]})

    for index, deps in enumerate(labels, start=1):
        agent = agent_returning(plan_payload(deps, workflow=graph(deps, scenario=f"WF-{index}")))
        result = agent.plan({"summary": f"需求 {index}"}, scenario_key=f"WF-{index}")
        assert result["approval_status"] == "pending"
        assert WorkflowPlannerAgent.dependencies_match(result["workflow"], deps), deps
