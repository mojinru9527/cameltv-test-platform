"""V16-004-R3：真实只读数据库连接拒绝写操作（DB 级验证，不靠 AST 推断）。"""
from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.aiqe.models.run import TestRun
from app.aiqe.services.query_registry import register_query
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.snapshot_service import ensure_snapshot
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.project import Project


def _readonly_engine(tmp_path):
    path = tmp_path / "readonly.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, project_id INTEGER, status TEXT)")
    conn.execute("INSERT INTO orders VALUES (1, 1, 'paid')")
    conn.commit()
    conn.close()
    # URI mode=ro：数据库连接层只读，写入必须由数据库自身拒绝。
    return create_engine(f"sqlite:///file:{path.as_posix()}?mode=ro&uri=true")


def test_readonly_database_rejects_insert_and_allows_select(tmp_path):
    engine = _readonly_engine(tmp_path)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, status FROM orders")).all()
        assert rows == [(1, "paid")]
        with pytest.raises(OperationalError) as exc:
            conn.execute(text("INSERT INTO orders (id, status) VALUES (2, 'x')"))
        assert "readonly" in str(exc.value).lower()
        with pytest.raises(OperationalError):
            conn.execute(text("UPDATE orders SET status='x'"))
        with pytest.raises(OperationalError):
            conn.execute(text("DELETE FROM orders"))


def test_query_registry_select_runs_on_readonly_engine(db_session, tmp_path):
    engine = _readonly_engine(tmp_path)
    if db_session.get(Project, 1) is None:
        db_session.add(Project(id=1, code="RO", name="RO", owner_id=1, status=1))
        db_session.flush()
    from app.aiqe.security import upsert_target_policy

    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["127.0.0.1"], "allowed_ports": [80, 443]},
    )
    register_query(
        db_session,
        project_id=1,
        query_key="ro_orders",
        statement="SELECT id, status FROM orders WHERE project_id = :project_id AND id = :order_id",
        allowed_params=["project_id", "order_id"],
        allowed_tables=["orders"],
        connection_ref="ro",
    )
    from app.aiqe.services import node_executor

    node_executor.default_connection_resolver = lambda ref: engine  # type: ignore[assignment]
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "db",
                "driver": "db",
                "depends_on": [],
                "input": {"query_key": "ro_orders", "params": {"order_id": 1}},
                "assertions": [
                    {
                        "assertion_key": "row_count",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-RO",
                        "type": "db_row_count",
                        "expected": 1,
                        "severity": "P0",
                    }
                ],
            }
        ],
        "edges": [],
    }
    from app.aiqe.services.capability_registry import register_manifest

    register_manifest(
        db_session,
        node_id="ro-db",
        driver_key="db",
        capabilities=["aiqe:db", "db.readonly"],
        platforms=["linux"],
        evidence_ref="evidence://ro-db",
    )
    workflow = create_workflow(db_session, project_id=1, graph=graph)
    approve_workflow(db_session, workflow.id, approved_by=1)
    ensure_snapshot(db_session, workflow)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="ro-db-e2e",
    )
    db_session.commit()
    from app.aiqe.services import job_consumer

    for _ in range(10):
        claimed = job_consumer.claim_aiqe_jobs(db_session)
        if not claimed:
            break
        for job_id in claimed:
            job_consumer.run_job(db_session, job_id)
        db_session.commit()
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    from sqlalchemy import select

    from app.aiqe.models.run import NodeRun, RunAssertionResult

    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assertions = list(db_session.scalars(select(RunAssertionResult)))
    assert run.outcome == "PASS", (
        run.outcome,
        run.status,
        node.status,
        node.error_class,
        [(a.status, a.error_text) for a in assertions],
        run.preflight_json,
    )
