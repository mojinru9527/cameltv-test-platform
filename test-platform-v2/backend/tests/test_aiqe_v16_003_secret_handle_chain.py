"""V16-003 验收：Secret Handle 全链路（真实 Worker + 真实 HTTP + 全库 Canary 扫描）。

对应规格 §V16-003：
- 登录响应返回 JWT / 随机 API token / Cookie；输出映射到下游节点；
- 下游节点在授权下真实使用 Handle（目标服务器确实收到 token）；
- 数据库所有 JSON/TEXT 列、API 响应、RunEvent、StepAttempt、Artifact、日志
  中的原始 Canary 命中数必须为 0；
- 错误 Project / Run / Node / 未授权 consumer 解析 Handle → 403/404 语义；
- Vault 不可用 → fail closed（不写明文）。
"""
from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import execution_service, job_consumer
from app.aiqe.services.run_context import RunContext
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.secret_vault import (
    SecretAccessDenied,
    SecretVault,
    create_secret_handle,
    resolve_secret_handle,
    revoke_secret_handle,
)
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.execution_job import ExecutionJob
from app.models.project import Project

#: 三类 Canary：JWT（值模式可识别）、随机 API token（仅靠输出分类）、Cookie 值。
JWT_CANARY = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ2MTYtY2FuYXJ5In0.c2lnbmF0dXJlLXYxNg"
API_TOKEN_CANARY = "tok_live_v16_9d3f4a7c2b8e5016"
COOKIE_CANARY = "sid_v16_cookie_8c1f2d9e"

_requests: list[dict] = []


class _SecretTarget(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length") or 0)
        self.rfile.read(length)
        _requests.append({"path": self.path, "headers": dict(self.headers)})
        if self.path == "/login":
            self._json(
                200,
                {
                    "access_token": JWT_CANARY,
                    "api_token": API_TOKEN_CANARY,
                    "session": {"sid": COOKIE_CANARY},
                    "user": {"id": 7},
                },
            )
            return
        self._json(404, {"error": "not found"})

    def do_GET(self):  # noqa: N802
        _requests.append({"path": self.path, "headers": dict(self.headers)})
        if self.path == "/profile":
            self._json(200, {"ok": True, "user": 7})
            return
        self._json(404, {"error": "not found"})

    def log_message(self, *args):
        return


@pytest.fixture()
def secret_target():
    _requests.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SecretTarget)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _ensure_project(db) -> None:
    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="V16SEC", name="V16 Secret", owner_id=1, status=1))
        db.flush()
    register_manifest(
        db,
        node_id="v16-secret-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://v16-secret-http",
    )


def _graph(port: int) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "login",
                "driver": "http",
                "depends_on": [],
                "input": {
                    "url": f"http://127.0.0.1:{port}/login",
                    "method": "POST",
                    "json": {"username": "qa", "password": "SuperSecret123"},
                    "expected_status": 200,
                },
                "outputs": {
                    "access_token": "$.json.access_token",
                    "api_token": "$.json.api_token",
                    "sid": "$.json.session.sid",
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "access_token": {"type": "string", "sensitive": True},
                        "api_token": {"type": "string", "sensitive": True},
                        "sid": {"type": "string", "sensitive": True},
                    },
                },
                "assertions": [
                    {
                        "assertion_key": "login_status",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-LOGIN-1",
                        "type": "http_status",
                        "expected": 200,
                        "severity": "P0",
                    }
                ],
            },
            {
                "key": "verify",
                "driver": "http",
                "depends_on": ["login"],
                "input": {
                    "url": f"http://127.0.0.1:{port}/profile",
                    "headers": {
                        "Authorization": "Bearer ${nodes.login.outputs.access_token}",
                        "X-Api-Token": "${nodes.login.outputs.api_token}",
                        "Cookie": "sid=${nodes.login.outputs.sid}",
                    },
                    "expected_status": 200,
                },
                "assertions": [
                    {
                        "assertion_key": "profile_status",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-PROFILE-1",
                        "type": "http_status",
                        "expected": 200,
                        "severity": "P0",
                    }
                ],
            },
        ],
        "edges": [{"from": "login", "to": "verify"}],
    }


@pytest.fixture()
def artifact_root(tmp_path):
    """把 Artifact 本地存储重定向到临时目录（Settings 是 pydantic 模型，需绕过校验）。"""
    from app.core.config import settings

    marker = object()
    previous = settings.__dict__.get("storage_dir", marker)
    object.__setattr__(settings, "storage_dir", str(tmp_path))
    try:
        yield tmp_path
    finally:
        if previous is marker:
            settings.__dict__.pop("storage_dir", None)
        else:
            object.__setattr__(settings, "storage_dir", previous)


def _scan_db_for(db, needle: str) -> list[str]:
    hits: list[str] = []
    inspector = inspect(db.bind)
    for table in inspector.get_table_names():
        if table.startswith("sqlite_"):
            continue
        columns = [column["name"] for column in inspector.get_columns(table)]
        for column in columns:
            try:
                rows = db.execute(
                    text(f'SELECT "{column}" FROM "{table}"')
                ).scalars().all()
            except Exception:
                db.rollback()
                continue
            for value in rows:
                if value is None:
                    continue
                if needle in str(value):
                    hits.append(f"{table}.{column}")
                    break
    return hits


def _run_secret_workflow(db, port: int, *, auth_headers=None):
    _ensure_project(db)
    upsert_target_policy(
        db,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [port],
            "allow_private_cidrs": ["127.0.0.0/8"],
            "max_redirects": 0,
        },
    )
    workflow = create_workflow(db, project_id=1, graph=_graph(port))
    approve_workflow(db, workflow.id, approved_by=1)
    db.flush()
    run = launch_run(
        db,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key=f"v16-secret-{port}",
    )
    db.commit()
    assert run.status == "RUNNING", run.preflight_json

    for _ in range(4):
        claimed = job_consumer.claim_aiqe_jobs(db, limit=2)
        if not claimed:
            break
        for job_id in claimed:
            job_consumer.run_job(db, job_id)
        db.expire_all()
        run = db.get(TestRun, run.id)
        if str(run.status) in {"COMPLETED", "BLOCKED", "ERROR"}:
            break
    db.expire_all()
    return run


# ── 1. 全链路：Handle 化 + 下游真实使用 + 全库 0 明文 ────────
def test_worker_secret_chain_persists_handles_and_zero_plaintext(
    db_session, secret_target, artifact_root
):
    port = secret_target
    run = _run_secret_workflow(db_session, port)

    login = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "login")
    )
    verify = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "verify")
    )
    assert login.status == "PASSED", login.error_class
    assert verify.status == "PASSED", verify.error_class

    refs = login.outputs_json
    for key in ("access_token", "api_token", "sid"):
        assert isinstance(refs[key], dict) and refs[key].get("secret_handle_id"), refs
        assert refs[key]["secret_ref"].startswith("vault://")
    # 下游节点在授权 scope 内真实拿到了明文并发送给目标服务器
    profile_requests = [item for item in _requests if item["path"] == "/profile"]
    assert profile_requests, _requests
    headers = {key.lower(): value for key, value in profile_requests[0]["headers"].items()}
    assert headers.get("authorization") == f"Bearer {JWT_CANARY}"
    assert headers.get("x-api-token") == API_TOKEN_CANARY
    assert COOKIE_CANARY in headers.get("cookie", "")

    # 全库扫描：任何列都不得出现原始 canary
    for canary in (JWT_CANARY, API_TOKEN_CANARY, COOKIE_CANARY):
        hits = _scan_db_for(db_session, canary)
        assert hits == [], f"canary 明文出现在 {hits}"

    # Artifact 文本文件同样 0 明文
    artifact_hits: list[str] = []
    for path in Path(artifact_root).rglob("*"):
        if path.is_file():
            try:
                if any(
                    canary in path.read_text(encoding="utf-8", errors="ignore")
                    for canary in (JWT_CANARY, API_TOKEN_CANARY, COOKIE_CANARY)
                ):
                    artifact_hits.append(str(path))
            except OSError:
                continue
    assert artifact_hits == [], f"canary 出现在 Artifact: {artifact_hits}"

    # Handle 访问审计：至少一条 ALLOW
    from app.aiqe.models.secret_handle import SecretAccessAudit, SecretHandle

    audits = list(db_session.scalars(select(SecretAccessAudit)))
    assert any(item.decision == "ALLOW" and item.consumer_node_key == "verify" for item in audits)

    # Run 终态后临时 Secret 必须被撤销（TTL/生命周期清理）
    handles = list(
        db_session.scalars(select(SecretHandle).where(SecretHandle.run_id == run.id))
    )
    assert handles, "登录输出应至少产生 3 个 Handle"
    assert all(item.revoked_at is not None for item in handles), [
        (item.key_name, item.revoked_at) for item in handles
    ]


# ── 2. Run Detail API 只返回遮蔽形式 ────────────────────────
def test_run_detail_api_masks_secret_handles(
    db_session, client, auth_headers, secret_target, artifact_root
):
    run = _run_secret_workflow(db_session, secret_target)

    for url in (
        f"/api/v1/aiqe/runs/{run.id}/nodes",
        f"/api/v1/aiqe/runs/{run.id}/attempts",
        f"/api/v1/aiqe/runs/{run.id}/events",
        f"/api/v1/aiqe/runs/{run.id}/assertions",
    ):
        resp = client.get(url, headers=auth_headers)
        assert resp.status_code == 200, (url, resp.text[:400])
        body = resp.text
        for canary in (JWT_CANARY, API_TOKEN_CANARY, COOKIE_CANARY):
            assert canary not in body, f"{url} 泄漏 canary"
        if url.endswith("/nodes"):
            assert "secret://" in body
            assert "vault://" not in body


# ── 3. Scope / TTL / 撤销 / consumer 拒绝 ───────────────────
def test_handle_resolution_scope_denials(db_session, secret_target):
    from datetime import UTC, datetime, timedelta

    _ensure_project(db_session)
    port = secret_target
    run = _run_secret_workflow(db_session, port)
    login = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "login")
    )
    handle_id = login.outputs_json["api_token"]["secret_handle_id"]
    vault = SecretVault()

    # 正确 scope：ALLOW（同一 Run 的下游节点）
    # 注意：生产 Vault 单例中的明文已在 Run 终态被撤销，这里用显式 vault 重建一条 Handle 验证解析规则。
    new_handle = create_secret_handle(
        db_session,
        project_id=1,
        run_id=run.id,
        producer_node_run_id=login.id,
        key_name="api_token",
        value=API_TOKEN_CANARY,
        allowed_consumer_nodes=["verify"],
        vault=vault,
    )
    assert (
        resolve_secret_handle(
            db_session,
            new_handle.id,
            project_id=1,
            run_id=run.id,
            consumer_node_key="verify",
            vault=vault,
        )
        == API_TOKEN_CANARY
    )

    # 未授权 consumer
    with pytest.raises(SecretAccessDenied) as exc:
        resolve_secret_handle(
            db_session,
            new_handle.id,
            project_id=1,
            run_id=run.id,
            consumer_node_key="other",
            vault=vault,
        )
    assert exc.value.code == "SECRET_HANDLE_CONSUMER_DENIED"

    # 错误 Project
    with pytest.raises(SecretAccessDenied) as exc:
        resolve_secret_handle(
            db_session,
            new_handle.id,
            project_id=2,
            run_id=run.id,
            consumer_node_key="verify",
            vault=vault,
        )
    assert exc.value.code == "SECRET_HANDLE_SCOPE_DENIED"

    # 错误 Run
    with pytest.raises(SecretAccessDenied) as exc:
        resolve_secret_handle(
            db_session,
            new_handle.id,
            project_id=1,
            run_id="other-run",
            consumer_node_key="verify",
            vault=vault,
        )
    assert exc.value.code == "SECRET_HANDLE_SCOPE_DENIED"

    # 过期
    with pytest.raises(SecretAccessDenied) as exc:
        resolve_secret_handle(
            db_session,
            new_handle.id,
            project_id=1,
            run_id=run.id,
            consumer_node_key="verify",
            vault=vault,
            now=datetime.now(UTC) + timedelta(days=2),
        )
    assert exc.value.code in {"SECRET_HANDLE_EXPIRED", "SECRET_VALUE_UNAVAILABLE"}

    # 撤销
    revoke_secret_handle(db_session, new_handle.id, vault=vault)
    with pytest.raises(SecretAccessDenied) as exc:
        resolve_secret_handle(
            db_session,
            new_handle.id,
            project_id=1,
            run_id=run.id,
            consumer_node_key="verify",
            vault=vault,
        )
    assert exc.value.code == "SECRET_HANDLE_REVOKED"

    # 审计：拒绝也要留痕
    from app.aiqe.models.secret_handle import SecretAccessAudit

    denials = [
        item
        for item in db_session.scalars(select(SecretAccessAudit))
        if item.handle_id == new_handle.id and item.decision == "DENY"
    ]
    assert denials


# ── 4. Vault 不可用：fail closed ────────────────────────────
def test_vault_unavailable_blocks_execution_without_plaintext(
    db_session, secret_target, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "use_external_secret_store", True)
    _ensure_project(db_session)
    port = secret_target
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [port],
            "allow_private_cidrs": ["127.0.0.0/8"],
        },
    )
    workflow = create_workflow(db_session, project_id=1, graph=_graph(port))
    approve_workflow(db_session, workflow.id, approved_by=1)
    db_session.flush()
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key="v16-vault-unavailable",
    )
    db_session.commit()
    # prepare_node 在派发阶段即 fail closed：Run 直接收口为 BLOCKED/INCOMPLETE。
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    assert run.status in {"BLOCKED", "COMPLETED", "ERROR"}
    assert run.outcome != "PASS"
    blocked_nodes = [
        row
        for row in db_session.scalars(select(NodeRun).where(NodeRun.run_id == run.id))
        if row.status == "BLOCKED"
    ]
    assert blocked_nodes, "Vault 不可用时节点必须 BLOCKED"
    login = next(row for row in blocked_nodes if row.node_key == "login")
    assert login.error_class == "SECRET_VAULT_UNAVAILABLE"
    claimed = job_consumer.claim_aiqe_jobs(db_session)
    for job_id in claimed:
        result = job_consumer.run_job(db_session, job_id)
        assert result.get("status") == "BLOCKED"
        assert result.get("error_class") == "SECRET_VAULT_UNAVAILABLE"
    assert _requests == [], "Vault 不可用时不得执行任何节点"
    for canary in (JWT_CANARY, API_TOKEN_CANARY, COOKIE_CANARY):
        assert _scan_db_for(db_session, canary) == []


# ── 5. 日志脱敏过滤器 ──────────────────────────────────────
def test_log_redaction_filter_scrubs_canaries(caplog):
    from app.aiqe.security.log_redaction import (
        install_log_redaction,
        register_known_secrets,
        reset_known_secrets,
    )

    caplog.set_level(logging.INFO)
    install_log_redaction()
    logger = logging.getLogger("app.aiqe.test")
    token = register_known_secrets([JWT_CANARY, API_TOKEN_CANARY, COOKIE_CANARY])
    try:
        logger.info("login token=%s", JWT_CANARY)
        logger.info("api=%s cookie=%s", API_TOKEN_CANARY, COOKIE_CANARY)
        try:
            raise RuntimeError(f"upstream failed with Authorization Bearer {JWT_CANARY}")
        except RuntimeError:
            logger.exception("node failed")
    finally:
        reset_known_secrets(token)
    text_all = "\n".join(record.getMessage() for record in caplog.records)
    text_all += "\n".join(record.exc_text or "" for record in caplog.records)
    assert JWT_CANARY not in text_all
    assert API_TOKEN_CANARY not in text_all
    assert COOKIE_CANARY not in text_all


# ── 6. 非字符串敏感值：脱敏而非 Handle（保持类型契约） ──────
def test_sensitive_non_string_value_is_redacted_not_handled(db_session):
    _ensure_project(db_session)
    run = TestRun(project_id=1, run_key="RUN-V16-SEC-TYPE", status="RUNNING")
    db_session.add(run)
    db_session.flush()
    node = NodeRun(run_id=run.id, node_key="login", driver_key="http")
    db_session.add(node)
    db_session.commit()
    ctx = RunContext(db_session, run.id, vault=SecretVault(), project_id=1)
    from app.aiqe.schemas.contracts import DriverResult

    result = DriverResult(
        driver_key="http",
        status="SUCCEEDED",
        data={"json": {"credentials": {"password": "NestedSecret!42", "user": "qa"}}},
    )
    stored = ctx.capture_node_outputs(
        node, result, {"credentials": "$.json.credentials"}
    )
    assert stored["credentials"]["password"] == "***"
    assert stored["credentials"]["user"] == "qa"
    assert "NestedSecret!42" not in json.dumps(stored, ensure_ascii=False)
