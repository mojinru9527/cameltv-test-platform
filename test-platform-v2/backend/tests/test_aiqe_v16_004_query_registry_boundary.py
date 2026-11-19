"""V16-004 验收：DB Query Registry 服务端化（AST allowlist / 表白名单 / 租户谓词 / 审计）。

覆盖规格 §V16-004：
- Workflow 只允许 `{query_key, query_version, params}`；inline SQL / allowed_tables /
  query_registry / connection_* 一律 BLOCKED；
- 登记查询由服务端加载 SQL，执行时再次 AST 校验；
- 表白名单缺失/越权、系统表、跨 schema、伪租户谓词、未审批、生产环境全部拒绝；
- 每次执行写 QueryExecutionAudit（成功/拒绝）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.query_registry import QueryExecutionAudit, RegisteredQuery
from app.aiqe.security import upsert_target_policy
from app.aiqe.security.sql_policy import SqlPolicyError, validate_select
from app.aiqe.services import job_consumer, node_executor, query_registry
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.query_registry import (
    DbReadonlyExecutor,
    QueryDenied,
    QueryNotRegistered,
    register_query,
)
from app.aiqe.services.workflow_validator import WorkflowValidationError, validate_workflow
from app.models.environment import Environment
from app.models.execution_job import ExecutionJob
from app.models.project import Project

GOOD_SQL = "SELECT id, status FROM orders WHERE project_id = :project_id AND id = :order_id"
RAW_SQL = "SELECT id, status FROM orders WHERE project_id = :project_id"


@pytest.fixture()
def target_db(tmp_path):
    db_file = Path(tmp_path) / "target.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE orders (id INTEGER PRIMARY KEY, project_id INTEGER, status TEXT)")
        )
        connection.execute(
            text(
                "CREATE TABLE secret_table (id INTEGER PRIMARY KEY, project_id INTEGER, secret TEXT)"
            )
        )
        connection.execute(
            text("INSERT INTO orders (id, project_id, status) VALUES (1, 1, 'live')")
        )
        connection.execute(
            text("INSERT INTO secret_table (id, project_id, secret) VALUES (1, 1, 'hidden')")
        )
    return engine


def _ensure_project(db, project_id: int = 1) -> None:
    if db.get(Project, project_id) is None:
        db.add(Project(id=project_id, code=f"V16Q{project_id}", name="V16 Q", owner_id=1, status=1))
        db.flush()
    register_manifest(
        db,
        node_id=f"v16-db-{project_id}",
        driver_key="db",
        capabilities=["db.readonly"],
        platforms=["linux"],
        evidence_ref="evidence://v16-db",
    )


def _seed_db_job(db, *, input_ref: dict, query_key: str = "order_status") -> tuple:
    _ensure_project(db)
    upsert_target_policy(
        db, project_id=1, environment_id=None, policy={"allowed_hosts": []}
    )
    run = TestRun(project_id=1, run_key="RUN-V16-Q", status="RUNNING")
    db.add(run)
    db.flush()
    graph = {
        "nodes": [
            {
                "key": "db_check",
                "driver": "db",
                "depends_on": [],
                "input": input_ref,
            }
        ],
        "edges": [],
    }
    node = NodeRun(
        run_id=run.id, node_key="db_check", driver_key="db", input_ref=dict(input_ref)
    )
    db.add(node)
    db.flush()
    job = ExecutionJob(
        project_id=1,
        kind="api",
        status="running",
        attempt=1,
        payload_json=json.dumps(
            {
                "run_id": run.id,
                "node_run_id": node.id,
                "driver": "db",
                "node_key": "db_check",
                "graph": graph,
            }
        ),
    )
    db.add(job)
    db.commit()
    return run, node, job


# ── 1. AST allowlist 单元矩阵 ───────────────────────────────
@pytest.mark.parametrize(
    ("statement", "allowed", "expect_code"),
    [
        ("SELECT id FROM orders WHERE project_id = :project_id", ["orders"], None),
        ("SELECT id FROM orders WHERE :project_id IS NOT NULL", ["orders"], "QUERY_TENANT_PREDICATE_INVALID"),
        ("SELECT id FROM orders, secret_table WHERE project_id = :project_id", ["orders"], "QUERY_TABLE_NOT_ALLOWED"),
        ("SELECT * FROM pg_class WHERE project_id = :project_id", ["pg_class"], "QUERY_SYSTEM_TABLE_DENIED"),
        ("DELETE FROM orders WHERE project_id = :project_id", ["orders"], "QUERY_NOT_SELECT"),
        ("SELECT 1; DROP TABLE orders", ["orders"], "QUERY_MULTI_STATEMENT"),
        ("SELECT pg_read_file('/etc/passwd') FROM orders WHERE project_id = :project_id", ["orders"], "QUERY_FUNCTION_DENIED"),
        (
            "WITH t AS (SELECT id FROM orders WHERE project_id = :project_id) SELECT * FROM t",
            ["orders", "t"],
            None,
        ),
    ],
)
def test_sql_policy_ast_matrix(statement, allowed, expect_code):
    if expect_code is None:
        result = validate_select(statement, allowed_tables=allowed)
        assert result.statement_hash.startswith("sha256:")
    else:
        with pytest.raises(SqlPolicyError) as exc:
            validate_select(statement, allowed_tables=allowed)
        assert exc.value.code == expect_code


# ── 2. 登记：AST 在登记期拒绝写/系统表/伪租户谓词 ───────────
def test_register_rejects_unsafe_sql(db_session):
    _ensure_project(db_session)
    for statement, params in (
        ("DELETE FROM orders WHERE project_id = :project_id", ["project_id"]),
        ("SELECT * FROM pg_class WHERE project_id = :project_id", ["project_id"]),
        ("SELECT id FROM orders WHERE :project_id IS NOT NULL", ["project_id"]),
        ("SELECT id FROM orders, secret_table WHERE project_id = :project_id", ["project_id"]),
    ):
        with pytest.raises(Exception):
            register_query(
                db_session,
                project_id=1,
                query_key="bad",
                statement=statement,
                allowed_params=params,
                allowed_tables=["orders"],
            )


def test_register_derives_allowed_tables_and_hash(db_session):
    _ensure_project(db_session)
    row = register_query(
        db_session,
        project_id=1,
        query_key="order_status",
        statement=GOOD_SQL,
        allowed_params=["project_id", "order_id"],
        allowed_tables=["orders"],
        approval_status="approved",
    )
    assert row.allowed_tables == ["orders"]
    assert row.statement_hash.startswith("sha256:")
    assert row.approval_status == "approved"


# ── 3. Worker 入口：合法登记查询成功 + 审计 ─────────────────
def test_worker_runs_registered_query_and_writes_audit(db_session, target_db, monkeypatch):
    monkeypatch.setattr(node_executor, "default_connection_resolver", lambda ref: target_db)
    register_query(
        db_session,
        project_id=1,
        query_key="order_status",
        statement=GOOD_SQL,
        allowed_params=["project_id", "order_id"],
        allowed_tables=["orders"],
        connection_ref="v16_test",
        approval_status="approved",
    )
    db_session.commit()
    _, node, job = _seed_db_job(
        db_session, input_ref={"query_key": "order_status", "params": {"order_id": 1}}
    )
    node.assertions_json = [
        {
            "assertion_key": "row_count",
            "oracle_layer": "REQ",
            "oracle_ref": "AC-DB-1",
            "type": "db_row_count",
            "expected": 1,
            "severity": "P0",
        }
    ]
    db_session.commit()
    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    assert result["status"] == "PASSED", (result.get("error_class"), node.error_class, node.output_ref.get("preflight"))
    assert node.status == "PASSED"
    job_row = db_session.get(ExecutionJob, job.id)
    assert '"row_count": 1' in (job_row.result_json or "")
    audits = list(db_session.scalars(__import__("sqlalchemy").select(QueryExecutionAudit)))
    assert audits and audits[0].policy_decision == "ALLOW"
    assert audits[0].query_key == "order_status"
    assert audits[0].query_hash.startswith("sha256:")
    assert audits[0].row_count == 1
    assert audits[0].executor_identity == "aiqe-worker"


# ── 4. Worker 入口：非法输入一律拒绝且零连接 ────────────────
@pytest.mark.parametrize(
    "input_ref",
    [
        {"sql": "SELECT * FROM orders"},
        {"query_key": "order_status", "params": {"order_id": 1}, "allowed_tables": ["orders"]},
        {
            "query_key": "order_status",
            "params": {"order_id": 1},
            "query_registry": {"order_status": {"sql": "SELECT 1"}},
        },
        {"query_key": "order_status", "params": {"order_id": 1}, "connection_url": "sqlite:///x"},
    ],
)
def test_worker_rejects_workflow_overrides_without_connecting(
    db_session, target_db, monkeypatch, input_ref
):
    calls: list[str] = []
    monkeypatch.setattr(
        node_executor, "default_connection_resolver", lambda ref: calls.append(ref) or target_db
    )
    _, node, job = _seed_db_job(db_session, input_ref=input_ref)
    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    assert result["status"] == "BLOCKED"
    assert node.error_class in {"INPUT_INVALID", "WORKFLOW_DB_OVERRIDE"}
    assert calls == [], "被拒绝的 DB 节点不得解析连接"


# ── 5. 执行期二次校验：绕过登记写入的坏数据也必须拒绝 ──────
def _insert_raw_query(db, *, statement: str, allowed_tables: list[str], approval: str = "approved"):
    _ensure_project(db)
    row = RegisteredQuery(
        project_id=1,
        query_key="raw_query",
        version=1,
        statement=statement,
        statement_hash="sha256:x",
        allowed_params=["project_id"],
        allowed_tables=allowed_tables,
        allowed_columns=[],
        approval_status=approval,
        max_rows=10,
        max_execution_ms=2000,
        connection_ref="v16_test",
        active=True,
    )
    db.add(row)
    db.commit()
    return row


def test_execution_revalidates_disallowed_table(db_session, target_db):
    _insert_raw_query(
        db_session,
        statement="SELECT secret FROM secret_table WHERE project_id = :project_id",
        allowed_tables=["orders"],
    )
    monkeypatch_target = target_db
    executor = DbReadonlyExecutor(connection_resolver=lambda ref: monkeypatch_target)
    with pytest.raises(QueryDenied) as exc:
        executor.execute(db_session, project_id=1, query_key="raw_query", params={})
    assert exc.value.code == "QUERY_TABLE_NOT_ALLOWED"
    audits = list(db_session.scalars(__import__("sqlalchemy").select(QueryExecutionAudit)))
    assert audits and audits[-1].policy_decision == "DENY"


def test_execution_rejects_fake_tenant_predicate(db_session, target_db):
    _insert_raw_query(
        db_session,
        statement="SELECT id FROM orders WHERE :project_id IS NOT NULL",
        allowed_tables=["orders"],
    )
    executor = DbReadonlyExecutor(connection_resolver=lambda ref: target_db)
    with pytest.raises(QueryDenied) as exc:
        executor.execute(db_session, project_id=1, query_key="raw_query", params={})
    assert exc.value.code == "QUERY_TENANT_PREDICATE_INVALID"


def test_execution_rejects_system_table(db_session, target_db):
    _insert_raw_query(
        db_session,
        statement="SELECT * FROM pg_class WHERE project_id = :project_id",
        allowed_tables=["pg_class"],
    )
    executor = DbReadonlyExecutor(connection_resolver=lambda ref: target_db)
    with pytest.raises(QueryDenied) as exc:
        executor.execute(db_session, project_id=1, query_key="raw_query", params={})
    assert exc.value.code == "QUERY_SYSTEM_TABLE_DENIED"


def test_execution_rejects_unapproved_query(db_session, target_db):
    _insert_raw_query(db_session, statement=RAW_SQL, allowed_tables=["orders"], approval="pending")
    executor = DbReadonlyExecutor(connection_resolver=lambda ref: target_db)
    with pytest.raises(QueryDenied) as exc:
        executor.execute(db_session, project_id=1, query_key="raw_query", params={"order_id": 1})
    assert exc.value.code == "QUERY_NOT_APPROVED"


def test_execution_rejects_cross_project_and_production_env(db_session, target_db):
    _insert_raw_query(db_session, statement=RAW_SQL, allowed_tables=["orders"])
    executor = DbReadonlyExecutor(connection_resolver=lambda ref: target_db)
    with pytest.raises(QueryNotRegistered):
        executor.execute(db_session, project_id=2, query_key="raw_query", params={"order_id": 1})

    env = Environment(
        project_id=1, name="prod", env_type="prod", base_url="", is_production=True
    )
    db_session.add(env)
    db_session.flush()
    with pytest.raises(QueryDenied) as exc:
        executor.execute(
            db_session,
            project_id=1,
            query_key="raw_query",
            params={"order_id": 1},
            environment_id=env.id,
        )
    assert exc.value.code == "PRODUCTION_DB_READ_FORBIDDEN"


def test_request_limits_can_only_tighten(db_session, target_db):
    _insert_raw_query(db_session, statement=RAW_SQL, allowed_tables=["orders"])
    executor = DbReadonlyExecutor(connection_resolver=lambda ref: target_db)
    result = executor.execute(
        db_session,
        project_id=1,
        query_key="raw_query",
        params={},
        requested_max_rows=1,
        requested_timeout_ms=1500,
    )
    assert result.row_count == 1
    assert result.max_rows == 1


# ── 6. Workflow Validator：DB 节点不得携带 SQL/白名单 ───────
def test_workflow_validator_rejects_db_override():
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "db",
                "driver": "db",
                "depends_on": [],
                "input": {
                    "query_key": "order_status",
                    "sql": "SELECT * FROM orders",
                    "allowed_tables": ["orders"],
                },
            }
        ],
        "edges": [],
    }
    with pytest.raises(WorkflowValidationError) as exc:
        validate_workflow(graph, registered_drivers={"db"})
    codes = {issue.code for issue in exc.value.issues}
    assert "db_workflow_override" in codes


def test_workflow_validator_requires_query_key():
    graph = {
        "schema_version": "1.0",
        "nodes": [{"key": "db", "driver": "db", "depends_on": [], "input": {}}],
        "edges": [],
    }
    with pytest.raises(WorkflowValidationError) as exc:
        validate_workflow(graph, registered_drivers={"db"})
    assert any(issue.code == "db_query_key_missing" for issue in exc.value.issues)


# ── 7. 管理 API：登记 → 审批 → 列表（项目隔离） ─────────────
def test_admin_query_registry_register_and_approve(
    db_session, client, auth_headers, target_db
):
    resp = client.post(
        "/api/v1/aiqe/admin/query-registry",
        headers=auth_headers,
        json={
            "query_key": "order_status_api",
            "statement": GOOD_SQL,
            "allowed_params": ["project_id", "order_id"],
            "allowed_tables": ["orders"],
            "connection_ref": "v16_test",
            "approval_status": "pending",
        },
    )
    assert resp.status_code == 200, resp.text
    created = resp.json()["data"]
    assert created["approval_status"] == "pending"
    assert created["allowed_tables"] == ["orders"]

    approve = client.post(
        f"/api/v1/aiqe/admin/query-registry/{created['id']}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["data"]["approval_status"] == "approved"

    listing = client.get("/api/v1/aiqe/admin/query-registry", headers=auth_headers)
    assert listing.status_code == 200
    keys = [item["query_key"] for item in listing.json()["data"]]
    assert "order_status_api" in keys


def test_admin_target_policy_write_and_list(db_session, client, auth_headers):
    resp = client.post(
        "/api/v1/aiqe/admin/target-policies",
        headers=auth_headers,
        json={
            "policy": {"allowed_hosts": ["api.example.test"], "allowed_ports": [443]},
            "name": "v16-admin",
        },
    )
    assert resp.status_code == 200, resp.text
    created = resp.json()["data"]
    assert created["version"] == 1
    assert created["policy"]["allowed_hosts"] == ["api.example.test"]

    listing = client.get("/api/v1/aiqe/admin/target-policies", headers=auth_headers)
    assert listing.status_code == 200
    assert listing.json()["data"]
