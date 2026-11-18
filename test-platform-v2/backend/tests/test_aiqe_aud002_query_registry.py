"""AUD-002：DB Read-only / Query Registry / 跨租户边界验收测试。

对应 v1.5 §01 AUD-002「验收测试」：
- 登记表 + 合法 project_id：PASS；
- 查询其他 project_id：服务端强制注入当前项目，绝不返回他人数据；
- DELETE/UPDATE/INSERT/DDL：登记阶段即拒绝（数据库账号只读为第二道防线）；
- Workflow 提交自定义 SQL / connection_url / allowed_tables：拒绝；
- 未登记 query_key：BLOCKED；
- 参数注入字符串只当参数值，不改变 SQL 结构；
- 查询超行数/超时：受控取消，Run 不挂死；
- 生产 DB 连接引用：默认不可用。
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.aiqe.drivers.db_readonly_driver import RowLimitExceeded
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.services import node_executor
from app.aiqe.services.query_registry import (
    DbReadonlyExecutor,
    QueryDenied,
    QueryNotRegistered,
    RegisteredQueryError,
    register_query,
    resolve_query,
)
from app.models.environment import Environment


def _readonly_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE matches (id INTEGER PRIMARY KEY, project_id INTEGER, "
                "status TEXT, phone TEXT, updated_at TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO matches (id, project_id, status, phone, updated_at) VALUES "
                "(1, 1, 'live', '13800000001', '2026-11-18'),"
                "(2, 2, 'draft', '13800000002', '2026-11-18'),"
                "(3, 1, 'draft', '13800000003', '2026-11-18')"
            )
        )
    return engine


MATCH_QUERY = (
    "SELECT id, status, phone FROM matches "
    "WHERE project_id = :project_id AND id = :match_id"
)


@pytest.fixture()
def readonly_engine():
    engine = _readonly_engine()
    try:
        yield engine
    finally:
        engine.dispose()


def _executor(engine):
    return DbReadonlyExecutor(connection_resolver=lambda ref: engine)


# ── 1. 登记校验（写语句 / 缺项目边界 / 参数不匹配） ────────
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE matches SET status='live' WHERE project_id = :project_id",
        "DELETE FROM matches WHERE project_id = :project_id",
        "DROP TABLE matches",
        "INSERT INTO matches (id, project_id) VALUES (9, :project_id)",
        "SELECT * FROM matches",
        "SELECT * FROM matches WHERE project_id = :project_id FOR UPDATE",
        "SELECT * FROM matches WHERE project_id = :project_id; SELECT 1",
        "SELECT * FROM pg_catalog.pg_tables WHERE project_id = :project_id",
    ],
)
def test_invalid_statements_rejected_at_registration(db_session, statement):
    with pytest.raises(RegisteredQueryError):
        register_query(
            db_session,
            project_id=1,
            query_key="bad",
            statement=statement,
            allowed_params=["project_id"],
            connection_ref="aiqe_test_readonly",
        )


def test_params_must_match_placeholders(db_session):
    with pytest.raises(RegisteredQueryError):
        register_query(
            db_session,
            project_id=1,
            query_key="mismatch",
            statement=MATCH_QUERY,
            allowed_params=["project_id"],  # 缺少 match_id
            connection_ref="ref",
        )
    with pytest.raises(RegisteredQueryError):
        register_query(
            db_session,
            project_id=1,
            query_key="extra",
            statement=MATCH_QUERY,
            allowed_params=["project_id", "match_id", "unused"],
            connection_ref="ref",
        )
    with pytest.raises(RegisteredQueryError):
        register_query(
            db_session,
            project_id=1,
            query_key="no-project",
            statement="SELECT id FROM matches WHERE id = :match_id",
            allowed_params=["match_id"],
            connection_ref="ref",
        )


def test_limits_validated(db_session):
    with pytest.raises(RegisteredQueryError):
        register_query(
            db_session,
            project_id=1,
            query_key="k",
            statement=MATCH_QUERY,
            allowed_params=["project_id", "match_id"],
            max_rows=0,
        )
    with pytest.raises(RegisteredQueryError):
        register_query(
            db_session,
            project_id=1,
            query_key="k",
            statement=MATCH_QUERY,
            allowed_params=["project_id", "match_id"],
            max_execution_ms=10,
        )


# ── 2. 解析与版本 ─────────────────────────────────────────
def test_register_versions_and_resolve(db_session):
    first = register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
        connection_ref="aiqe_test_readonly",
    )
    second = register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
        connection_ref="aiqe_test_readonly",
    )
    assert first.version == 1 and second.version == 2
    assert resolve_query(db_session, project_id=1, query_key="verify_match_status").version == 2
    assert (
        resolve_query(
            db_session, project_id=1, query_key="verify_match_status", version=1
        ).id
        == first.id
    )


def test_unregistered_and_cross_project_lookup(db_session):
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
    )
    with pytest.raises(QueryNotRegistered):
        resolve_query(db_session, project_id=1, query_key="not_registered")
    with pytest.raises(QueryNotRegistered):
        # 项目 2 没有登记该 key，不能借用项目 1 的模板
        resolve_query(db_session, project_id=2, query_key="verify_match_status")


# ── 3. 执行：正常 / 项目边界 / 参数化 ───────────────────────
def _register_and_run(db_session, engine, *, project_id=1, params=None, match_id=1):
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
        connection_ref="aiqe_test_readonly",
        max_rows=10,
    )
    return _executor(engine).execute(
        db_session,
        project_id=project_id,
        query_key="verify_match_status",
        params={"project_id": project_id, "match_id": match_id, **(params or {})},
    )


def test_registered_query_executes_and_returns_rows(db_session, readonly_engine):
    result = _register_and_run(db_session, readonly_engine)
    assert result.row_count == 1
    assert result.rows[0]["id"] == 1
    assert result.rows[0]["status"] == "live"
    assert result.query_key == "verify_match_status"
    assert result.query_version == 1
    assert result.query_hash.startswith("sha256:")
    assert result.rows_digest.startswith("sha256:")
    # 敏感列被脱敏
    assert result.rows[0]["phone"] == "***"
    assert result.params_redacted["project_id"] == 1


def test_project_id_is_injected_server_side(db_session, readonly_engine):
    # 客户端伪造 project_id=2，但执行器必须使用服务端 project_id=1
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
        connection_ref="aiqe_test_readonly",
        max_rows=10,
    )
    result = _executor(readonly_engine).execute(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        params={"project_id": 2, "match_id": 2},
    )
    assert result.row_count == 0, "不得读取其他 Project 的数据"
    assert result.params_redacted["project_id"] == 2  # 原始入参记录（脱敏后）


def test_cross_project_lookup_denied(db_session, readonly_engine):
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
    )
    with pytest.raises(QueryNotRegistered):
        _executor(readonly_engine).execute(
            db_session,
            project_id=2,
            query_key="verify_match_status",
            params={"match_id": 2},
        )


def test_unregistered_query_denied(db_session, readonly_engine):
    with pytest.raises(QueryNotRegistered):
        _executor(readonly_engine).execute(
            db_session, project_id=1, query_key="whatever", params={}
        )


def test_unknown_param_rejected(db_session, readonly_engine):
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
    )
    with pytest.raises(QueryDenied) as excinfo:
        _executor(readonly_engine).execute(
            db_session,
            project_id=1,
            query_key="verify_match_status",
            params={"match_id": 1, "evil": "x"},
        )
    assert excinfo.value.code == "INVALID_PARAM"


def test_string_injection_does_not_change_sql(db_session, readonly_engine):
    register_query(
        db_session,
        project_id=1,
        query_key="inject",
        statement="SELECT id, status FROM matches WHERE project_id = :project_id AND status = :status",
        allowed_params=["project_id", "status"],
    )
    result = _executor(readonly_engine).execute(
        db_session,
        project_id=1,
        query_key="inject",
        params={"status": "live' OR '1'='1"},
    )
    assert result.row_count == 0


def test_row_limit_enforced(db_session, readonly_engine):
    register_query(
        db_session,
        project_id=1,
        query_key="too_many",
        statement="SELECT id FROM matches WHERE project_id = :project_id",
        allowed_params=["project_id"],
        max_rows=1,
    )
    with pytest.raises(RowLimitExceeded):
        _executor(readonly_engine).execute(
            db_session, project_id=1, query_key="too_many"
        )


def test_production_environment_denied(db_session, readonly_engine):
    env = Environment(project_id=1, name="prod", env_type="prod", is_production=True)
    db_session.add(env)
    db_session.flush()
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
    )
    with pytest.raises(QueryDenied) as excinfo:
        _executor(readonly_engine).execute(
            db_session,
            project_id=1,
            query_key="verify_match_status",
            params={"match_id": 1},
            environment_id=env.id,
        )
    assert excinfo.value.code == "PRODUCTION_DB_READ_FORBIDDEN"


def test_missing_connection_reference_denied(db_session, monkeypatch):
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
        connection_ref="not_configured_ref",
    )
    executor = DbReadonlyExecutor()  # 默认 resolver，配置为空
    with pytest.raises(QueryDenied) as excinfo:
        executor.execute(
            db_session,
            project_id=1,
            query_key="verify_match_status",
            params={"match_id": 1},
        )
    assert excinfo.value.code == "CONNECTION_NOT_CONFIGURED"


# ── 4. 节点执行器：只接受 query_key ────────────────────────
def _seed_run_with_node(db, *, input_ref: dict) -> NodeRun:
    run = TestRun(project_id=1, run_key="RUN-AUD002", status="RUNNING")
    db.add(run)
    db.flush()
    node = NodeRun(run_id=run.id, node_key="db", driver_key="db", input_ref=input_ref)
    db.add(node)
    db.commit()
    return node


def test_node_executor_runs_registered_query(db_session, readonly_engine, monkeypatch):
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=MATCH_QUERY,
        allowed_params=["project_id", "match_id"],
    )
    monkeypatch.setattr(node_executor, "default_connection_resolver", lambda ref: readonly_engine)
    node = _seed_run_with_node(
        db_session,
        input_ref={"query_key": "verify_match_status", "params": {"match_id": 1}},
    )
    outcome = node_executor.execute_node(node, db=db_session)
    assert outcome.status == "PASSED", outcome
    assert outcome.detail["query_key"] == "verify_match_status"
    assert outcome.detail["summary"]["row_count"] == 1
    assert outcome.detail["rows"][0]["phone"] == "***"


@pytest.mark.parametrize(
    "input_ref",
    [
        {"query_key": "verify_match_status", "sql": "SELECT * FROM matches"},
        {"query_key": "verify_match_status", "connection_url": "postgresql://evil/db"},
        {"query_key": "verify_match_status", "allowed_tables": ["*"]},
        {"query_key": "verify_match_status", "statement": "DELETE FROM matches"},
    ],
)
def test_node_executor_rejects_workflow_db_overrides(db_session, input_ref):
    node = _seed_run_with_node(db_session, input_ref=input_ref)
    outcome = node_executor.execute_node(node, db=db_session)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class == "WORKFLOW_DB_OVERRIDE"


def test_node_executor_requires_query_key(db_session):
    node = _seed_run_with_node(db_session, input_ref={"sql": "SELECT 1"})
    outcome = node_executor.execute_node(node, db=db_session)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class == "INPUT_INVALID"


def test_node_executor_unregistered_query_blocked(db_session):
    node = _seed_run_with_node(db_session, input_ref={"query_key": "missing"})
    outcome = node_executor.execute_node(node, db=db_session)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class == "QUERY_NOT_REGISTERED"
