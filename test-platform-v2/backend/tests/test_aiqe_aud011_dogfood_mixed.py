"""AUD-011：真实跨系统 Mixed Workflow Dogfood 验收测试。

用一个真实的本地 HTTP 服务（登录 / 建赛事 / 公共 API）+ 真实 SQLite 只读 Query Registry
驱动一条 API → DB 的混合链路，验证：

- 同一 TestRun 内多 Driver 真实执行；
- 动态输出（match_id）来自真实上一步，无硬编码；
- 每节点有 required 断言并落库；
- 令牌不进入 NodeRun/Event 明文；
- 缺配置/缺 Runner 时 BLOCKED，而不是 Mock PASS。
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.services import node_executor
from app.aiqe.services.dogfood import (
    DogfoodConfig,
    DogfoodConfigError,
    build_sports_mixed_graph,
    report_digest,
    run_dogfood,
)
from app.aiqe.services.query_registry import register_query

TOKEN = "tok-dogfood-abc"
PASSWORD = "DogfoodPass!42"


class _SportsStub(BaseHTTPRequestHandler):
    """最小真实服务：/api/auth/login、/api/admin/matches、/api/public/matches/{id}。"""

    matches: dict[str, dict] = {}
    db_engine = None

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/auth/login":
            if payload.get("username") == "qa_admin" and payload.get("password") == PASSWORD:
                self._json(200, {"data": {"access_token": TOKEN, "user": {"id": 7}}})
                return
            self._json(401, {"error": "bad credentials"})
            return
        if self.path == "/api/admin/matches":
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self._json(403, {"error": "forbidden"})
                return
            match_id = f"m-{len(self.matches) + 1}"
            self.matches[match_id] = {
                "match_id": match_id,
                "project_id": 1,
                "status": "live",
                "name": payload.get("name", ""),
            }
            if _SportsStub.db_engine is not None:
                from sqlalchemy import text

                with _SportsStub.db_engine.begin() as connection:
                    connection.execute(
                        text(
                            "INSERT INTO matches (match_id, project_id, status) "
                            "VALUES (:match_id, 1, 'live')"
                        ),
                        {"match_id": match_id},
                    )
            self._json(201, {"data": {"match_id": match_id}})
            return
        self._json(404, {"error": "not found"})

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/public/matches/"):
            match_id = self.path.rsplit("/", 1)[-1]
            match = self.matches.get(match_id)
            if match is None:
                self._json(404, {"error": "not found"})
                return
            self._json(200, {"data": match})
            return
        self._json(404, {"error": "not found"})

    def log_message(self, *args):
        return


@pytest.fixture()
def sports_server():
    _SportsStub.matches = {}
    _SportsStub.db_engine = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SportsStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        _SportsStub.db_engine = None


def _readonly_engine(tmp_path):
    """文件型 SQLite：服务端真实写入，AIQE 侧以只读连接查询（与生产同构）。"""
    db_file = tmp_path / "sports.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE matches (match_id TEXT PRIMARY KEY, project_id INTEGER, status TEXT)"
            )
        )
    return engine


def _write_engine(tmp_path):
    """被测服务的写连接：必须独立于只读执行器（PRAGMA query_only 是连接级设置）。"""
    db_file = tmp_path / "sports.db"
    return create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})


def _config(port: int, *, db_query_key: str = "", include_public_ui: bool = False) -> DogfoodConfig:
    return DogfoodConfig(
        project_id=1,
        base_url=f"http://127.0.0.1:{port}",
        admin_url="",
        admin_username="qa_admin",
        admin_password=PASSWORD,
        db_query_key=db_query_key,
        include_public_ui=include_public_ui,
        allow_private_targets=True,
        fixture_namespace="aiqe-dogfood-test",
    )


def test_graph_contains_required_nodes_and_assertions():
    graph = build_sports_mixed_graph(_config(8000, db_query_key="verify_match_status"))
    keys = [node["key"] for node in graph["nodes"]]
    assert keys == ["login", "create_match", "verify_public_api", "verify_db_readonly"]
    for node in graph["nodes"]:
        assert node["input"]["assertions"], node["key"]
    login = graph["nodes"][0]["input"]
    assert login["outputs"]["access_token"]["sensitive"] is True
    # 公共 API 校验使用动态 match_id 模板，不是硬编码
    assert "${nodes.create_match.outputs.match_id}" in graph["nodes"][2]["input"]["url_template"]


def test_missing_config_refuses_to_fake_pass():
    with pytest.raises(DogfoodConfigError):
        DogfoodConfig(project_id=1, base_url="", fixture_namespace="x").validate()
    with pytest.raises(DogfoodConfigError):
        DogfoodConfig(project_id=1, base_url="http://x", fixture_namespace="").validate()
    with pytest.raises(DogfoodConfigError):
        DogfoodConfig(
            project_id=1,
            base_url="http://x",
            fixture_namespace="x",
            include_admin_ui=True,  # 缺 admin_url / 管理员账号
        ).validate()


@pytest.fixture()
def admin_policy(db_session, sports_server):
    """V16-001：策略由管理员预先配置，dogfood 不得自行授权私网。"""
    from app.aiqe.security import upsert_target_policy

    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [sports_server],
            "allow_private_cidrs": ["127.0.0.0/8"],
            "max_redirects": 0,
        },
    )
    db_session.commit()
    yield


def test_mixed_api_and_db_run_passes_with_real_drivers(
    db_session, sports_server, monkeypatch, tmp_path, admin_policy
):
    engine = _readonly_engine(tmp_path)
    _SportsStub.db_engine = _write_engine(tmp_path)
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=(
            "SELECT match_id, status FROM matches "
            "WHERE project_id = :project_id AND match_id = :match_id"
        ),
        allowed_params=["project_id", "match_id"],
        connection_ref="dogfood_test",
    )
    db_session.commit()
    monkeypatch.setattr(node_executor, "default_connection_resolver", lambda ref: engine)

    reports = run_dogfood(db_session, _config(sports_server, db_query_key="verify_match_status"))
    assert len(reports) == 1
    report = reports[0]
    assert report.status == "COMPLETED", report.payload()
    assert report.outcome == "PASS", report.payload()
    assert set(report.node_statuses) == {
        "login",
        "create_match",
        "verify_public_api",
        "verify_db_readonly",
    }
    assert all(status == "PASSED" for status in report.node_statuses.values())
    assert report.assertions_total >= 6
    assert report.assertions_failed == 0
    assert report.dynamic_propagation_ok is True
    assert report.secret_plaintext_hits == 0
    assert report.production_safe is True
    assert report_digest(report)

    # 断言落库 + 动态输出可追溯 + 令牌不落明文
    run = db_session.get(TestRun, report.run_id)
    assert run.source_type == "dogfood"
    nodes = list(db_session.scalars(__import__("sqlalchemy").select(NodeRun).where(NodeRun.run_id == run.id)))
    created = next(node for node in nodes if node.node_key == "create_match")
    match_id = created.output_ref["match_id"]
    assert match_id.startswith("m-")
    verify = next(node for node in nodes if node.node_key == "verify_public_api")
    assert match_id in verify.input_ref["url"]
    for node in nodes:
        assert TOKEN not in json.dumps(node.output_ref, ensure_ascii=False)
    assertion_rows = db_session.execute(
        __import__("sqlalchemy").select(RunAssertionResult)
        .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
        .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
        .where(NodeRun.run_id == run.id)
    ).all()
    assert len(assertion_rows) >= 6


def test_ui_node_without_runner_blocks_instead_of_pass(db_session, sports_server, admin_policy):
    report = run_dogfood(
        db_session, _config(sports_server, include_public_ui=True)
    )[0]
    assert report.node_statuses.get("verify_frontend") == "BLOCKED"
    assert report.outcome != "PASS"
    assert report.unverified_platforms == ["web_desktop"]
    assert report.verified_platforms == []


def test_repeated_runs_use_isolated_fixture_namespaces(
    db_session, sports_server, monkeypatch, tmp_path, admin_policy
):
    engine = _readonly_engine(tmp_path)
    _SportsStub.db_engine = _write_engine(tmp_path)
    register_query(
        db_session,
        project_id=1,
        query_key="verify_match_status",
        statement=(
            "SELECT match_id, status FROM matches "
            "WHERE project_id = :project_id AND match_id = :match_id"
        ),
        allowed_params=["project_id", "match_id"],
        connection_ref="dogfood_test",
    )
    db_session.commit()
    monkeypatch.setattr(node_executor, "default_connection_resolver", lambda ref: engine)
    reports = run_dogfood(
        db_session, _config(sports_server, db_query_key="verify_match_status"), runs=3
    )
    assert len(reports) == 3
    namespaces = {report.fixture_namespace for report in reports}
    assert len(namespaces) == 3
    assert all(report.outcome == "PASS" for report in reports)


def test_wrong_credentials_fail_run_not_pass(db_session, sports_server, admin_policy):
    config = DogfoodConfig(
        project_id=1,
        base_url=f"http://127.0.0.1:{sports_server}",
        admin_username="qa_admin",
        admin_password="wrong-password",
        allow_private_targets=True,
        fixture_namespace="aiqe-dogfood-fail",
    )
    report = run_dogfood(db_session, config)[0]
    assert report.status == "COMPLETED"
    assert report.outcome == "FAIL"
    assert report.node_statuses["login"] == "FAILED"
    assert report.assertions_failed >= 1


def test_missing_policy_blocks_dogfood_before_any_node(db_session):
    """V16-001：无服务端 TargetPolicy 时 dogfood 不得自动授权并执行。"""
    config = DogfoodConfig(
        project_id=1,
        base_url="http://127.0.0.1:9",
        admin_username="qa_admin",
        admin_password=PASSWORD,
        allow_private_targets=True,  # 调用方开关不再能生成私网授权
        fixture_namespace="aiqe-dogfood-blocked",
    )
    report = run_dogfood(db_session, config)[0]
    assert report.status == "BLOCKED"
    assert report.outcome != "PASS"
    assert report.node_statuses == {}
    assert report.blocked_steps
    assert report.blocked_steps[0]["error_class"] in {
        "RUN_ENVIRONMENT_MISSING",
        "NO_POLICY_CONFIGURED",
    }


def test_policy_without_target_port_blocks_node(db_session):
    """策略存在但未授权目标端口：节点 BLOCKED，且不产生 PASS。"""
    from app.aiqe.security import upsert_target_policy

    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [1],
            "allow_private_cidrs": ["127.0.0.0/8"],
        },
    )
    db_session.commit()
    config = DogfoodConfig(
        project_id=1,
        base_url="http://127.0.0.1:9",
        admin_username="qa_admin",
        admin_password=PASSWORD,
        allow_private_targets=True,
        fixture_namespace="aiqe-dogfood-port-denied",
    )
    report = run_dogfood(db_session, config)[0]
    assert report.node_statuses["login"] == "BLOCKED"
    assert report.outcome != "PASS"
    assert report.blocked_steps
