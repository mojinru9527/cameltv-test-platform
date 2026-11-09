"""M2 / TA-009：Workflow Validator 单测（13 号 §6.2）。"""
from __future__ import annotations

import copy

import pytest

from app.aiqe.services.workflow_validator import (
    WorkflowValidationError,
    validate_workflow,
    workflow_checksum,
)

DRIVERS = {"http", "playwright"}
CAPS = {"api.http.request", "ui.state"}


def sample() -> dict:
    return {
        "schema_version": "1.0",
        "scenario_key": "SPORT-LIVE-PUBLISH-001",
        "nodes": [
            {
                "key": "create_match",
                "type": "action",
                "driver": "http",
                "capability": "api.http.request",
                "depends_on": [],
                "input": {"method": "POST", "body_ref": "fixture:match.valid"},
                "outputs": {"match_id": "$.data.id"},
                "assertions": [{"key": "http_ok", "type": "http_status", "expected": 200}],
                "retry_policy": {"max_attempts": 1},
                "idempotency_key_expr": "${inputs.body_ref}",
            },
            {
                "key": "configure",
                "type": "action",
                "driver": "playwright",
                "capability": "ui.state",
                "depends_on": ["create_match"],
                "input": {"variables": {"match_id": "${nodes.create_match.outputs.match_id}"}},
                "assertions": [{"key": "publish", "type": "ui_state", "expected": "success"}],
                "retry_policy": {"max_attempts": 1},
            },
        ],
        "edges": [{"from": "create_match", "to": "configure", "condition": "success"}],
        "run_policy": {"max_parallel_nodes": 2, "fail_fast": False},
    }


def check(graph, **kwargs):
    validate_workflow(
        graph,
        registered_drivers=kwargs.pop("drivers", DRIVERS),
        registered_capabilities=kwargs.pop("caps", CAPS),
    )


def test_valid_sample_passes():
    check(sample())


def test_schema_version_required():
    graph = sample()
    del graph["schema_version"]
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "schema_version_missing" for i in exc.value.issues)


def test_duplicate_node_key():
    graph = sample()
    graph["nodes"][1]["key"] = "create_match"
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "node_key_duplicate" for i in exc.value.issues)


def test_missing_dependency():
    graph = sample()
    graph["nodes"][1]["depends_on"] = ["ghost"]
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "node_dependency_missing" for i in exc.value.issues)


def test_dependency_cycle():
    graph = sample()
    graph["nodes"][0]["depends_on"] = ["configure"]
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    codes = {i.code for i in exc.value.issues}
    assert "dependency_cycle" in codes


def test_unregistered_driver():
    graph = sample()
    graph["nodes"][0]["driver"] = "unknown"
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "driver_unregistered" for i in exc.value.issues)


def test_unregistered_capability():
    graph = sample()
    graph["nodes"][0]["capability"] = "api.unknown"
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "capability_unregistered" for i in exc.value.issues)


def test_variable_unknown_node():
    graph = sample()
    graph["nodes"][1]["input"]["variables"]["match_id"] = "${nodes.ghost.outputs.match_id}"
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "variable_node_unknown" for i in exc.value.issues)


def test_variable_not_ancestor():
    graph = sample()
    graph["nodes"][1]["depends_on"] = []
    graph["edges"] = []
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "variable_node_not_ancestor" for i in exc.value.issues)


def test_variable_output_unknown():
    graph = sample()
    graph["nodes"][1]["input"]["variables"]["match_id"] = "${nodes.create_match.outputs.nope}"
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "variable_output_unknown" for i in exc.value.issues)


def test_non_idempotent_write_retry_rejected():
    graph = sample()
    graph["nodes"][0]["retry_policy"] = {"max_attempts": 3}
    del graph["nodes"][0]["idempotency_key_expr"]
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "non_idempotent_retry" for i in exc.value.issues)


def test_write_retry_with_idempotency_key_passes():
    graph = sample()
    graph["nodes"][0]["retry_policy"] = {"max_attempts": 3}
    check(graph)


def test_assertion_expected_required():
    graph = sample()
    del graph["nodes"][1]["assertions"][0]["expected"]
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "assertion_expected_missing" for i in exc.value.issues)


def test_exploratory_assertion_allowed_without_expected():
    graph = sample()
    graph["nodes"][1]["assertions"] = [{"key": "explore", "type": "exploratory"}]
    check(graph)


def test_edge_must_match_depends_on():
    graph = sample()
    graph["edges"].append({"from": "configure", "to": "create_match"})
    with pytest.raises(WorkflowValidationError) as exc:
        check(graph)
    assert any(i.code == "edge_not_in_depends_on" for i in exc.value.issues)


def test_checksum_is_canonical_and_content_sensitive():
    a = sample()
    b = copy.deepcopy(a)
    # 键顺序不同但内容相同 → checksum 相同
    b = {key: b[key] for key in reversed(list(b.keys()))}
    assert workflow_checksum(a) == workflow_checksum(b)

    b["nodes"][0]["timeout_ms"] = 15000
    assert workflow_checksum(a) != workflow_checksum(b)
