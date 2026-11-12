"""P0：条件边（success / failure / always）单测。"""
from __future__ import annotations

import uuid

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services.dag_scheduler import schedule

GRAPH = {
    "schema_version": "1.0",
    "nodes": [
        {"key": "probe", "driver": "http", "depends_on": []},
        {"key": "recover", "driver": "http", "depends_on": ["probe"]},
    ],
    "edges": [{"from": "probe", "to": "recover", "condition": "failure"}],
    "run_policy": {"max_parallel_nodes": 1},
}


def make_run(db):
    run = TestRun(project_id=1, run_key=f"run-{uuid.uuid4()}", status="RUNNING")
    db.add(run)
    db.flush()
    return run


def test_failure_edge_fires_only_on_failure(db_session):
    run = make_run(db_session)
    rows = schedule(db_session, run.id, GRAPH)
    by_key = {row.node_key: row for row in rows}
    assert by_key["probe"].status == "READY"
    assert by_key["recover"].status == "PENDING"

    by_key["probe"].status = "FAILED"
    rows = schedule(db_session, run.id, GRAPH)
    by_key = {row.node_key: row for row in rows}
    assert by_key["recover"].status == "READY"


def test_failure_edge_does_not_fire_on_success(db_session):
    run = make_run(db_session)
    rows = schedule(db_session, run.id, GRAPH)
    by_key = {row.node_key: row for row in rows}
    by_key["probe"].status = "PASSED"
    rows = schedule(db_session, run.id, GRAPH)
    by_key = {row.node_key: row for row in rows}
    assert by_key["recover"].status == "PENDING"
