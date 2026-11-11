"""M5 / TA-029：Change Impact Agent 单测。"""
from __future__ import annotations

import json

import pytest

from app.aiqe.agents.base import AgentSchemaError
from app.aiqe.agents.change_impact_agent import ChangeImpactAgent, compute_impact


def output(areas, suites, forced, rationale=""):
    return {
        "impacted_areas": areas,
        "candidate_suites": suites,
        "forced_suites": forced,
        "rationale": rationale,
    }


def agent(data: dict) -> ChangeImpactAgent:
    return ChangeImpactAgent(lambda system, user: json.dumps(data, ensure_ascii=False))


def test_auth_change_forces_auth_and_smoke():
    impact = compute_impact(["test-platform-v2/backend/app/api/v1/auth.py"])
    assert "auth" in impact["impacted_areas"]
    assert impact["forced_suites"] == ["auth-suite", "smoke-suite"]


def test_union_of_multiple_areas():
    impact = compute_impact(["backend/app/api/live.py", "backend/app/services/payment.py"])
    assert impact["impacted_areas"] == ["api", "live", "payment"]
    assert impact["candidate_suites"] == [
        "api-suite",
        "live-suite",
        "payment-suite",
        "smoke-suite",
    ]


def test_unknown_change_defaults_to_smoke():
    assert compute_impact(["README.md"])["candidate_suites"] == ["smoke-suite"]


def test_valid_agent_output():
    files = ["backend/app/api/v1/login.py"]
    expected = compute_impact(files)
    data = output(expected["impacted_areas"], expected["candidate_suites"], expected["forced_suites"])
    result = agent(data).analyze(files)
    assert result["forced_suites"] == ["auth-suite", "smoke-suite"]


def test_omitted_forced_suite_rejected():
    files = ["backend/app/api/v1/auth_permission.py"]
    with pytest.raises(AgentSchemaError):
        agent(output(["auth"], ["auth-suite"], ["auth-suite"])).analyze(files)


def test_omitted_auth_area_rejected():
    files = ["backend/app/api/v1/auth_permission.py"]
    with pytest.raises(AgentSchemaError):
        agent(output(["live"], ["auth-suite", "smoke-suite"], ["auth-suite", "smoke-suite"])).analyze(files)


def test_empty_files_rejected():
    with pytest.raises(AgentSchemaError):
        agent(output(["unknown"], ["smoke-suite"], [])).analyze([])
