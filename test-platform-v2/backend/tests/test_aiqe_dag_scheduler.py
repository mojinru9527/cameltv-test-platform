"""M2 / TA-010：DAG Scheduler 单测（串行/并行/失败阻断/恢复/资源锁）。"""
from __future__ import annotations

import pytest

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import dag_scheduler


def make_run(db, key="RUN-DAG-0001", status="QUEUED") -> TestRun:
    run = TestRun(project_id=1, run_key=key, source_type="manual", status=status)
    db.add(run)
    db.flush()
    return run


def diamond(max_parallel: int = 2, fail_fast: bool = False) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {"key": "A", "driver": "http", "depends_on": [], "resource_keys": []},
            {"key": "B", "driver": "http", "depends_on": ["A"]},
            {"key": "C", "driver": "http", "depends_on": ["A"]},
            {"key": "D", "driver": "http", "depends_on": ["B", "C"]},
        ],
        "edges": [
            {"from": "A", "to": "B"},
            {"from": "A", "to": "C"},
            {"from": "B", "to": "D"},
            {"from": "C", "to": "D"},
        ],
        "run_policy": {"max_parallel_nodes": max_parallel, "fail_fast": fail_fast},
    }


def statuses(db, run_id):
    rows = db.query(NodeRun).filter_by(run_id=run_id).all()
    return {row.node_key: row.status for row in rows}


def test_serial_parallel_join_and_complete(db_session):
    run = make_run(db_session)
    graph = diamond()
    dispatched: list[str] = []
    dag_scheduler.schedule(db_session, run.id, graph, dispatch=lambda n: dispatched.append(n.node_key))
    assert dispatched == ["A"]

    dag_scheduler.complete_node(db_session, run.id, "A", "PASSED", graph)
    dispatched.clear()
    dag_scheduler.schedule(db_session, run.id, graph, dispatch=lambda n: dispatched.append(n.node_key))
    assert sorted(dispatched) == ["B", "C"]

    dag_scheduler.complete_node(db_session, run.id, "B", "PASSED", graph)
    dag_scheduler.complete_node(db_session, run.id, "C", "PASSED", graph)
    dispatched.clear()
    dag_scheduler.schedule(db_session, run.id, graph, dispatch=lambda n: dispatched.append(n.node_key))
    assert dispatched == ["D"]

    dag_scheduler.complete_node(db_session, run.id, "D", "PASSED", graph)
    db_session.refresh(run)
    assert run.status == "COMPLETED"
    assert run.outcome == "PASS"


def test_parallel_limit_one(db_session):
    run = make_run(db_session)
    graph = diamond(max_parallel=1)
    dispatched: list[str] = []
    dag_scheduler.schedule(db_session, run.id, graph, dispatch=lambda n: dispatched.append(n.node_key))
    dag_scheduler.complete_node(db_session, run.id, "A", "PASSED", graph)
    dispatched.clear()
    dag_scheduler.schedule(db_session, run.id, graph, dispatch=lambda n: dispatched.append(n.node_key))
    assert len(dispatched) == 1
    assert statuses(db_session, run.id)["D"] == "PENDING"


def test_fail_fast_blocks_run(db_session):
    run = make_run(db_session)
    graph = diamond(fail_fast=True)
    dag_scheduler.schedule(db_session, run.id, graph)
    dag_scheduler.complete_node(db_session, run.id, "A", "PASSED", graph)
    dag_scheduler.schedule(db_session, run.id, graph)
    dag_scheduler.complete_node(db_session, run.id, "B", "FAILED", graph)
    db_session.refresh(run)
    assert run.status == "BLOCKED"
    assert run.outcome is None
    assert statuses(db_session, run.id)["C"] == "BLOCKED"


def test_resource_lock_blocks_second_run(db_session):
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {"key": "A", "driver": "http", "depends_on": [], "resource_keys": ["fixture:match"]}
        ],
        "edges": [],
        "run_policy": {"max_parallel_nodes": 1, "fail_fast": False},
    }
    run1 = make_run(db_session, key="RUN-LOCK-1")
    run2 = make_run(db_session, key="RUN-LOCK-2")
    dag_scheduler.schedule(db_session, run1.id, graph)
    dag_scheduler.schedule(db_session, run2.id, graph)
    assert statuses(db_session, run2.id)["A"] == "PENDING"

    dag_scheduler.complete_node(db_session, run1.id, "A", "PASSED", graph)
    dag_scheduler.schedule(db_session, run2.id, graph)
    assert statuses(db_session, run2.id)["A"] == "READY"


def test_recover_resumes_running_node(db_session):
    run = make_run(db_session)
    graph = diamond()
    dag_scheduler.schedule(db_session, run.id, graph)
    node = db_session.query(NodeRun).filter_by(run_id=run.id, node_key="A").one()
    node.status = "RUNNING"
    db_session.flush()

    dispatched: list[str] = []
    dag_scheduler.recover(db_session, run.id, graph, dispatch=lambda n: dispatched.append(n.node_key))
    assert "A" in dispatched
    assert statuses(db_session, run.id)["A"] == "READY"


def test_cleanup_node_runs_after_terminal(db_session):
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {"key": "A", "driver": "http", "depends_on": []},
            {"key": "cleanup", "type": "cleanup", "driver": "http", "depends_on": []},
        ],
        "edges": [],
        "run_policy": {"max_parallel_nodes": 2, "cleanup_node": "cleanup"},
    }
    run = make_run(db_session)
    dag_scheduler.schedule(db_session, run.id, graph)
    dag_scheduler.complete_node(db_session, run.id, "A", "PASSED", graph)

    dispatched: list[str] = []
    dag_scheduler.schedule(db_session, run.id, graph, dispatch=lambda n: dispatched.append(n.node_key))
    assert dispatched == ["cleanup"]
    dag_scheduler.complete_node(db_session, run.id, "cleanup", "PASSED", graph)
    db_session.refresh(run)
    assert run.status == "COMPLETED" and run.outcome == "PASS"
