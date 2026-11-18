"""AUD-003：动态输出 / Artifact / Prompt 全链路 Secret 防护验收测试。

对应 v1.5 §01 AUD-003「验收测试」：
- 字段名规则与值模式分类（password/token/JWT/Bearer/PEM/AKIA/sk-/canary）；
- 持久化前脱敏：NodeRun.output_ref / StepAttempt / ExecutionJob.result_json / RunEvent；
- 端到端 canary：真实本地服务返回唯一 canary token，扫描全部落库字段明文命中 = 0；
- Secret Handle：合法下游可取用；跨 Run / 跨 Project / 非白名单节点 / 过期 / 撤销全部拒绝。
"""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import select

from app.aiqe.models.event import RunEvent
from app.aiqe.models.run import NodeRun, StepAttempt, TestRun
from app.aiqe.models.secret_handle import SecretHandle
from app.aiqe.redaction import (
    CLASSIFIER,
    Redactor,
    SecretLeakError,
    assert_no_secret,
    contains_secret,
    redact_mapping,
)
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.aiqe.services.run_context import RunContext
from app.aiqe.services.secret_vault import (
    SecretAccessDenied,
    SecretHandleError,
    SecretVault,
    create_secret_handle,
    resolve_secret_handle,
    revoke_secret_handle,
)
from app.models.execution_job import ExecutionJob

CANARY = "CANARY_SECRET_aud003_7f3c9d"


# ── 1. 分类器：字段名 ──────────────────────────────────────
@pytest.mark.parametrize(
    "key",
    [
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "authorization",
        "Authorization",
        "cookie",
        "set-cookie",
        "api_key",
        "apiKey",
        "private_key",
        "client_secret",
        "signing_key",
        "session_id",
        "otp",
        "phone",
        "email",
        "id_card",
    ],
)
def test_sensitive_keys_detected(key):
    assert CLASSIFIER.is_sensitive_key(key) is True


@pytest.mark.parametrize("key", ["match_id", "status", "user_id", "duration_ms", "url", "title"])
def test_non_sensitive_keys_allowed(key):
    assert CLASSIFIER.is_sensitive_key(key) is False


# ── 2. 分类器：值模式 ──────────────────────────────────────
@pytest.mark.parametrize(
    "text",
    [
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abcdefgh",
        "Authorization: Bearer abcdefghijklmnop",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
        "AKIAIOSFODNN7EXAMPLE",
        "sk-abcdefghijklmnopqrstuvwx",
        'access_token="abcdefghijklmnop"',
        CANARY,
    ],
)
def test_secret_value_patterns_detected(text):
    assert CLASSIFIER.contains_secret(text) is True
    assert contains_secret(text) is True


def test_plain_values_not_flagged():
    assert CLASSIFIER.contains_secret("match_id=12345 status=live") is False
    assert contains_secret({"match_id": "123", "status": "live"}) is False


# ── 3. 脱敏映射 ───────────────────────────────────────────
def test_redact_mapping_masks_nested_sensitive_fields():
    payload = {
        "request": {
            "url": "https://api.allowed.test/login",
            "headers": {"Authorization": "Bearer abcdefghijklmnop", "X-Trace": "t-1"},
        },
        "response": {
            "status_code": 200,
            "body": json.dumps(
                {"access_token": CANARY, "refresh_token": "refresh-123", "match_id": "m-1"}
            ),
        },
        "match_id": "m-1",
    }
    redacted = redact_mapping(payload)
    text = json.dumps(redacted, ensure_ascii=False)
    assert CANARY not in text
    assert "refresh-123" not in text
    assert "abcdefghijklmnop" not in text
    assert redacted["match_id"] == "m-1"
    assert "m-1" in text  # 非敏感字段保留
    assert redacted["request"]["headers"]["Authorization"] == "***"
    assert redacted["request"]["headers"]["X-Trace"] == "t-1"


def test_redact_text_handles_json_and_plain():
    redactor = Redactor()
    masked = redactor.redact_text(json.dumps({"token": CANARY, "ok": True}))
    assert CANARY not in masked
    assert '"ok": true' in masked
    plain = redactor.redact_text(f"login failed with access_token={CANARY} retry")
    assert CANARY not in plain
    assert "retry" in plain


def test_assert_no_secret_raises_on_leak():
    assert_no_secret({"match_id": "1"})
    with pytest.raises(SecretLeakError):
        assert_no_secret({"payload": CANARY})
    with pytest.raises(SecretLeakError):
        assert_no_secret({"access_token": "plain-token-value"})


# ── 4. 端到端 canary：真实 HTTP 节点落库零明文 ──────────────
class _LoginHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = json.dumps(
            {
                "access_token": CANARY,
                "refresh_token": f"{CANARY}-refresh",
                "match_id": "match-42",
                "status": "live",
            }
        ).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


@pytest.fixture()
def login_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoginHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _scan_tables_for(db, needle: str) -> list[str]:
    hits: list[str] = []
    for node in db.scalars(select(NodeRun)):
        if needle in json.dumps(node.output_ref or {}, ensure_ascii=False):
            hits.append(f"node_runs.output_ref:{node.node_key}")
    for attempt in db.scalars(select(StepAttempt)):
        if needle in json.dumps(attempt.output_summary_json or {}, ensure_ascii=False):
            hits.append(f"step_attempts.output_summary_json:{attempt.step_key}")
        if attempt.error_json and needle in json.dumps(attempt.error_json, ensure_ascii=False):
            hits.append(f"step_attempts.error_json:{attempt.step_key}")
    for job in db.scalars(select(ExecutionJob)):
        if needle in (job.result_json or ""):
            hits.append(f"execution_jobs.result_json:{job.id}")
        if needle in (job.error_message or ""):
            hits.append(f"execution_jobs.error_message:{job.id}")
    for event in db.scalars(select(RunEvent)):
        if needle in json.dumps(event.payload_json or {}, ensure_ascii=False):
            hits.append(f"run_events.payload:{event.event_type}")
    return hits


def test_canary_token_never_persisted(db_session, login_server, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "aiqe_http_allow_private", True)
    port = login_server
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [port],
            "allow_private_cidrs": ["127.0.0.0/8"],
            "allowed_methods": ["POST", "GET"],
        },
    )
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "login",
                "driver": "http",
                "input": {
                    "url": f"http://127.0.0.1:{port}/login",
                    "method": "POST",
                    "json": {"username": "qa", "password": "SuperSecret123"},
                    "expected_status": 200,
                },
                # v1.4 起输出必须显式声明（Assertion Runtime / capture_node_outputs）。
                "outputs": {
                    "match_id": "$.json.match_id",
                    "status": "$.json.status",
                },
            }
        ],
        "edges": [],
    }
    run = TestRun(project_id=1, run_key="RUN-AUD003", source_type="manual", status="QUEUED")
    db_session.add(run)
    db_session.flush()
    dag_scheduler.create_node_runs(db_session, run.id, graph)
    dag_scheduler.schedule(
        db_session, run.id, graph, dispatch=lambda row: enqueue_node_run(db_session, row, graph=graph)
    )
    db_session.commit()
    job = db_session.scalar(select(ExecutionJob).where(ExecutionJob.status == "pending"))

    job_consumer.claim_aiqe_jobs(db_session)
    outcome = job_consumer.run_job(db_session, job.id)
    assert outcome["node_status"] == "PASSED", outcome

    db_session.expire_all()
    hits = _scan_tables_for(db_session, CANARY)
    assert hits == [], f"canary 明文出现在: {hits}"

    # 非敏感业务数据仍可追溯（动态输出没有被一刀切抹掉）
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    stored = json.dumps(node.output_ref, ensure_ascii=False)
    assert "match-42" in stored
    assert "live" in stored
    # 请求体里的 password 也不得明文落库
    assert "SuperSecret123" not in stored


# ── 5. Secret Handle 生命周期 ──────────────────────────────
def _seed_run(db, key="RUN-SECRET-1", project_id=1) -> tuple[TestRun, NodeRun, NodeRun]:
    run = TestRun(project_id=project_id, run_key=key, status="RUNNING")
    db.add(run)
    db.flush()
    producer = NodeRun(run_id=run.id, node_key="login", driver_key="http")
    consumer = NodeRun(run_id=run.id, node_key="verify", driver_key="http")
    db.add_all([producer, consumer])
    db.commit()
    return run, producer, consumer


def test_handle_allows_listed_consumer_only(db_session):
    vault = SecretVault()
    run, producer, _consumer = _seed_run(db_session)
    handle = create_secret_handle(
        db_session,
        project_id=1,
        run_id=run.id,
        producer_node_run_id=producer.id,
        key_name="access_token",
        value=CANARY,
        allowed_consumer_nodes=("verify",),
        vault=vault,
    )
    assert handle.secret_ref == f"vault://{handle.id}"
    assert CANARY not in json.dumps(handle.metadata_json or {})

    value = resolve_secret_handle(
        db_session,
        handle.id,
        project_id=1,
        run_id=run.id,
        consumer_node_key="verify",
        vault=vault,
    )
    assert value == CANARY

    with pytest.raises(SecretAccessDenied) as excinfo:
        resolve_secret_handle(
            db_session,
            handle.id,
            project_id=1,
            run_id=run.id,
            consumer_node_key="other_node",
            vault=vault,
        )
    assert excinfo.value.code == "SECRET_HANDLE_CONSUMER_DENIED"


def test_handle_rejects_cross_run_and_cross_project(db_session):
    vault = SecretVault()
    run, producer, _ = _seed_run(db_session, key="RUN-SECRET-2", project_id=1)
    other_run, _, _ = _seed_run(db_session, key="RUN-SECRET-3", project_id=1)
    handle = create_secret_handle(
        db_session,
        project_id=1,
        run_id=run.id,
        producer_node_run_id=producer.id,
        key_name="token",
        value=CANARY,
        vault=vault,
    )
    with pytest.raises(SecretAccessDenied) as excinfo:
        resolve_secret_handle(
            db_session,
            handle.id,
            project_id=1,
            run_id=other_run.id,
            consumer_node_key="verify",
            vault=vault,
        )
    assert excinfo.value.code == "SECRET_HANDLE_SCOPE_DENIED"

    with pytest.raises(SecretAccessDenied):
        resolve_secret_handle(
            db_session,
            handle.id,
            project_id=2,
            run_id=run.id,
            consumer_node_key="verify",
            vault=vault,
        )


def test_handle_expiry_and_revocation(db_session):
    vault = SecretVault()
    run, producer, _ = _seed_run(db_session, key="RUN-SECRET-4")
    handle = create_secret_handle(
        db_session,
        project_id=1,
        run_id=run.id,
        producer_node_run_id=producer.id,
        key_name="token",
        value=CANARY,
        ttl_seconds=60,
        vault=vault,
        now=datetime.now(UTC) - timedelta(minutes=5),
    )
    with pytest.raises(SecretAccessDenied) as excinfo:
        resolve_secret_handle(
            db_session,
            handle.id,
            project_id=1,
            run_id=run.id,
            consumer_node_key="verify",
            vault=vault,
        )
    assert excinfo.value.code == "SECRET_HANDLE_EXPIRED"

    fresh = create_secret_handle(
        db_session,
        project_id=1,
        run_id=run.id,
        producer_node_run_id=producer.id,
        key_name="token2",
        value=CANARY,
        vault=vault,
    )
    revoke_secret_handle(db_session, fresh.id, vault=vault)
    with pytest.raises(SecretAccessDenied) as excinfo:
        resolve_secret_handle(
            db_session,
            fresh.id,
            project_id=1,
            run_id=run.id,
            consumer_node_key="verify",
            vault=vault,
        )
    assert excinfo.value.code == "SECRET_HANDLE_REVOKED"


def test_handle_rejects_unknown_run_or_node(db_session):
    run, producer, _ = _seed_run(db_session, key="RUN-SECRET-5")
    with pytest.raises(SecretHandleError):
        create_secret_handle(
            db_session,
            project_id=1,
            run_id="missing-run",
            producer_node_run_id=producer.id,
            key_name="token",
            value=CANARY,
            vault=SecretVault(),
        )
    with pytest.raises(SecretHandleError):
        create_secret_handle(
            db_session,
            project_id=1,
            run_id=run.id,
            producer_node_run_id="missing-node",
            key_name="token",
            value=CANARY,
            vault=SecretVault(),
        )
    with pytest.raises(SecretHandleError):
        create_secret_handle(
            db_session,
            project_id=1,
            run_id=run.id,
            producer_node_run_id=producer.id,
            key_name="token",
            value="",
            vault=SecretVault(),
        )


# ── 6. RunContext：敏感输出 → Handle，下游解析 ──────────────
def test_run_context_writes_handle_and_resolves_downstream(db_session):
    vault = SecretVault()
    run, producer, _ = _seed_run(db_session, key="RUN-SECRET-6")
    ctx = RunContext(
        db_session,
        run.id,
        handle_resolver=lambda handle_id, node_key: resolve_secret_handle(
            db_session,
            handle_id,
            project_id=1,
            run_id=run.id,
            consumer_node_key=node_key,
            vault=vault,
        ),
    )
    stored = ctx.set_output_secure(
        "login",
        {"access_token": CANARY, "match_id": "m-7", "user": {"email": "qa@example.com"}},
        project_id=1,
        allowed_consumer_nodes=("verify",),
        vault=vault,
    )
    row = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "login"))
    assert CANARY not in json.dumps(row.output_ref, ensure_ascii=False)
    assert "qa@example.com" not in json.dumps(row.output_ref, ensure_ascii=False)
    assert stored["access_token"]["secret_handle_id"]
    assert row.output_ref["match_id"] == "m-7"

    handle_id = stored["access_token"]["secret_handle_id"]
    resolved = ctx.resolve_inputs(
        "verify", {"auth": "${nodes.login.outputs.access_token}", "id": "${nodes.login.outputs.match_id}"}
    )
    assert resolved == {"auth": CANARY, "id": "m-7"}

    direct = ctx.resolve_inputs("verify", "${secret_handles." + handle_id + "}")
    assert direct == CANARY
