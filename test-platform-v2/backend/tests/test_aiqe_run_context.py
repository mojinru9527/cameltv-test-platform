"""M2 / TA-011：RunContext 单测（变量解析 / secret / 隔离 / 调度集成）。"""
from __future__ import annotations

import pytest

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import dag_scheduler
from app.aiqe.services.run_context import (
    RunContext,
    SecretLeakError,
    VariableResolutionError,
)


def make_run(db, key="RUN-CTX-1", status="RUNNING") -> TestRun:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status=status)
    db.add(run)
    db.flush()
    return run


def make_node(db, run_id, key="A", output=None) -> NodeRun:
    node = NodeRun(
        run_id=run_id, node_key=key, driver_key="http", status="PASSED", output_ref=output or {}
    )
    db.add(node)
    db.flush()
    return node


def test_set_output_and_read(db_session):
    run = make_run(db_session)
    make_node(db_session, run.id)
    ctx = RunContext(db_session, run.id)
    ctx.set_output("A", {"match_id": 42})
    ctx.set_output("A", {"extra": True})
    assert ctx.output("A") == {"match_id": 42, "extra": True}


def test_resolve_typed_and_nested(db_session):
    run = make_run(db_session)
    make_node(db_session, run.id, output={"match_id": 42, "meta": {"ok": True}})
    ctx = RunContext(db_session, run.id)
    assert ctx.resolve("${nodes.A.outputs.match_id}") == 42
    payload = {
        "id": "${nodes.A.outputs.match_id}",
        "flag": "${nodes.A.outputs.meta}",
        "list": ["${nodes.A.outputs.match_id}", 1],
    }
    assert ctx.resolve(payload) == {"id": 42, "flag": {"ok": True}, "list": [42, 1]}


def test_string_interpolation(db_session):
    run = make_run(db_session)
    make_node(db_session, run.id, output={"match_id": "m-1"})
    ctx = RunContext(db_session, run.id)
    assert ctx.resolve("match/${nodes.A.outputs.match_id}") == "match/m-1"


def test_missing_references(db_session):
    run = make_run(db_session)
    make_node(db_session, run.id, output={"x": 1})
    ctx = RunContext(db_session, run.id)
    with pytest.raises(VariableResolutionError):
        ctx.resolve("${nodes.ghost.outputs.x}")
    with pytest.raises(VariableResolutionError):
        ctx.resolve("${nodes.A.outputs.nope}")
    with pytest.raises(VariableResolutionError):
        ctx.resolve("${unknown.ref}")


def test_secrets_resolution_and_errors(db_session):
    run = make_run(db_session)
    make_node(db_session, run.id)
    ctx = RunContext(db_session, run.id)
    assert ctx.resolve("${secrets.API_TOKEN}", secrets={"API_TOKEN": "s3cr3t"}) == "s3cr3t"
    with pytest.raises(VariableResolutionError):
        ctx.resolve("${secrets.API_TOKEN}")


def test_set_output_rejects_secret_ref(db_session):
    run = make_run(db_session)
    make_node(db_session, run.id)
    ctx = RunContext(db_session, run.id)
    with pytest.raises(SecretLeakError):
        ctx.set_output("A", {"token": "${secrets.API_TOKEN}"})


def test_snapshot_redacts_secrets(db_session):
    run = make_run(db_session)
    make_node(db_session, run.id, output={"token_ref": "${secrets.API_TOKEN}", "plain": "ok"})
    ctx = RunContext(db_session, run.id)
    snap = ctx.snapshot(secrets={"API_TOKEN": "s3cr3t"})
    assert snap["A"]["token_ref"] == "***"
    assert snap["A"]["plain"] == "ok"


def test_run_scope_isolation(db_session):
    run1 = make_run(db_session, "RUN-CTX-A")
    run2 = make_run(db_session, "RUN-CTX-B")
    make_node(db_session, run1.id, key="A", output={"v": 1})
    make_node(db_session, run2.id, key="A", output={"v": 2})
    assert RunContext(db_session, run1.id).resolve("${nodes.A.outputs.v}") == 1
    assert RunContext(db_session, run2.id).resolve("${nodes.A.outputs.v}") == 2


def test_scheduler_writes_outputs(db_session):
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {"key": "A", "driver": "http", "depends_on": []},
            {"key": "B", "driver": "http", "depends_on": ["A"]},
        ],
        "edges": [{"from": "A", "to": "B"}],
        "run_policy": {"max_parallel_nodes": 2, "fail_fast": False},
    }
    run = make_run(db_session, status="QUEUED")
    dag_scheduler.schedule(db_session, run.id, graph)
    dag_scheduler.complete_node(
        db_session, run.id, "A", "PASSED", graph, outputs={"match_id": "m-9"}
    )
    ctx = RunContext(db_session, run.id)
    assert ctx.resolve("${nodes.A.outputs.match_id}") == "m-9"
    assert ctx.snapshot()["A"]["match_id"] == "m-9"
