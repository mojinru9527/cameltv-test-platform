"""v1.4 FIX-001：RunContext Resolver 验收测试。"""
from __future__ import annotations

import pytest

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.schemas.contracts import DriverResult
from app.aiqe.services.run_context import (
    RunContext,
    VariableResolutionError,
)


def _run(db, key="RUN-CTX-V2"):
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="RUNNING")
    db.add(run)
    db.flush()
    return run


def _node(db, run_id, key, *, output=None, status="PASSED"):
    node = NodeRun(
        run_id=run_id,
        node_key=key,
        driver_key="http",
        status=status,
        outputs_json=output or {},
        output_ref=output or {},
    )
    db.add(node)
    db.flush()
    return node


def test_secret_fixture_env_syntax(db_session):
    run = _run(db_session)
    _node(db_session, run.id, "A", output={"token": "t-1"})
    ctx = RunContext(
        db_session,
        run.id,
        secrets={"TOKEN": "s3cr3t"},
        fixtures={"user": {"name": "qa"}},
        environ={"BASE_URL": "https://api.test"},
    )
    resolved = ctx.resolve_node_input(
        "B",
        {
            "auth": "Bearer ${SECRET:TOKEN}",
            "uid": "${FIXTURE:user}",
            "url": "${ENV:BASE_URL}/x",
            "token": "${nodes.A.outputs.token}",
        },
    )
    assert resolved.values["auth"] == "Bearer s3cr3t"
    assert resolved.values["uid"] == {"name": "qa"}
    assert resolved.values["url"] == "https://api.test/x"
    assert resolved.values["token"] == "t-1"
    assert resolved.secret_keys == ["TOKEN"]
    assert {ref.kind for ref in resolved.source_refs} == {
        "secret",
        "fixture",
        "env",
        "node_output",
    }


def test_secret_not_persisted_in_resolved_input(db_session):
    run = _run(db_session, "RUN-CTX-V2-2")
    node = _node(db_session, run.id, "B", status="PENDING")
    ctx = RunContext(db_session, run.id, secrets={"TOKEN": "s3cr3t"})
    resolved = ctx.resolve_node_input("B", {"authorization": "Bearer ${SECRET:TOKEN}"})
    ctx.persist_resolved_input(node, resolved)
    assert resolved.values["authorization"] == "Bearer s3cr3t"
    assert "s3cr3t" not in str(node.resolved_input_json)
    assert node.resolved_input_json["authorization"] == "***"
    assert node.secret_keys_json == ["TOKEN"]


def test_missing_fixture_and_secret_error_codes(db_session):
    run = _run(db_session, "RUN-CTX-V2-3")
    ctx = RunContext(db_session, run.id, secrets={}, fixtures={})
    with pytest.raises(VariableResolutionError) as secret:
        ctx.resolve_node_input("B", {"token": "${SECRET:NOPE}"})
    assert secret.value.code == "SECRET_UNAVAILABLE"
    with pytest.raises(VariableResolutionError) as fixture:
        ctx.resolve_node_input("B", {"user": "${FIXTURE:nope}"})
    assert fixture.value.code == "FIXTURE_NOT_FOUND"


def test_non_ancestor_reference_blocked(db_session):
    run = _run(db_session, "RUN-CTX-V2-4")
    _node(db_session, run.id, "A", output={"v": 1})
    _node(db_session, run.id, "C", output={"v": 3})
    graph = {
        "nodes": [
            {"key": "A", "depends_on": []},
            {"key": "B", "depends_on": ["A"]},
            {"key": "C", "depends_on": []},
        ],
        "edges": [{"from": "A", "to": "B"}],
    }
    ctx = RunContext(db_session, run.id, graph=graph)
    with pytest.raises(VariableResolutionError) as exc:
        ctx.resolve_node_input("B", {"x": "${nodes.C.outputs.v}"})
    assert exc.value.code == "VARIABLE_NOT_ANCESTOR"


def test_capture_outputs_jsonpath_and_schema(db_session):
    run = _run(db_session, "RUN-CTX-V2-5")
    node = _node(db_session, run.id, "A")
    ctx = RunContext(db_session, run.id)
    result = DriverResult(
        driver_key="http",
        status="SUCCEEDED",
        data={"json": {"data": {"id": 42, "name": "match"}}},
    )
    outputs = ctx.capture_node_outputs(
        node,
        result,
        {"match_id": "$.json.data.id", "name": "$.json.data.name"},
        output_schema={
            "type": "object",
            "required": ["match_id", "name"],
            "properties": {"match_id": {"type": "integer"}},
        },
    )
    assert outputs == {"match_id": 42, "name": "match"}
    assert node.outputs_json == outputs
    assert node.output_ref == outputs


def test_capture_outputs_schema_mismatch_blocks(db_session):
    run = _run(db_session, "RUN-CTX-V2-6")
    node = _node(db_session, run.id, "A")
    ctx = RunContext(db_session, run.id)
    result = DriverResult(
        driver_key="http", status="SUCCEEDED", data={"json": {"id": "x"}}
    )
    with pytest.raises(VariableResolutionError) as exc:
        ctx.capture_node_outputs(
            node,
            result,
            {"id": "$.json.id"},
            output_schema={"type": "object", "properties": {"id": {"type": "integer"}}},
        )
    assert exc.value.code == "OUTPUT_SCHEMA_MISMATCH"


def test_run_isolation_concurrent_values(db_session):
    run1 = _run(db_session, "RUN-CTX-ISO-1")
    run2 = _run(db_session, "RUN-CTX-ISO-2")
    _node(db_session, run1.id, "A", output={"v": 1})
    _node(db_session, run2.id, "A", output={"v": 2})
    assert RunContext(db_session, run1.id).resolve("${nodes.A.outputs.v}") == 1
    assert RunContext(db_session, run2.id).resolve("${nodes.A.outputs.v}") == 2
