"""V16-001 验收：HTTP/DB 无策略必须 fail-closed（真实 Worker 入口）。

对应规格 `V16-001：删除 HTTP / DB 的 fail-open Legacy Fallback`：

- `execute_inprocess_job()`（Worker 正式入口）在创建任何 Driver 前解析策略；
- 无 Environment / 无 Policy / Resolver 异常 / 策略被删除 / 策略过期 → BLOCKED；
- 拒绝时目标服务器收到 0 个请求、数据库收到 0 条语句；
- 节点执行记录保存策略决策、版本、hash 与拒绝原因；
- 静态扫描证明旧 `_execute_http` / `_execute_db` 不再存在于正式执行链。
"""
from __future__ import annotations

import inspect
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import app.aiqe
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.security import (
    ExecutionCapabilities,
    PolicyDecision,
    TargetPolicy,
    resolve_execution_policy,
    upsert_target_policy,
)
from app.aiqe.services import event_service, job_consumer, node_executor
from app.models.environment import Environment
from app.models.execution_job import ExecutionJob
from app.models.project import Project


# ── 受控目标服务器：统计真实收到的请求数 ─────────────────────
class _CountingHandler(BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 约定
        type(self).hits += 1
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


@pytest.fixture()
def target_server():
    _CountingHandler.hits = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CountingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


# ── 造数：Run / NodeRun / ExecutionJob（Worker 认领后的状态） ──
def _ensure_project(db, project_id: int = 1) -> None:
    if db.get(Project, project_id) is None:
        db.add(Project(id=project_id, code=f"V16{project_id}", name="V16", owner_id=1, status=1))
        db.flush()


def _ensure_environment(db, *, project_id: int = 1, base_url: str = "") -> Environment:
    _ensure_project(db, project_id)
    env = Environment(
        project_id=project_id,
        name="v16-test",
        env_type="test",
        base_url=base_url,
        is_production=False,
    )
    db.add(env)
    db.flush()
    return env


def _seed_job(db, *, url: str, driver: str = "http", environment_id: int | None = None, project_id: int = 1):
    _ensure_project(db, project_id)
    run = TestRun(
        project_id=project_id,
        run_key=f"RUN-V16-{uuid.uuid4().hex[:8]}",
        status="RUNNING",
        environment_id=environment_id,
    )
    db.add(run)
    db.flush()
    graph = {
        "nodes": [
            {"key": "api", "driver": driver, "depends_on": [], "input": {"url": url}}
        ],
        "edges": [],
    }
    node = NodeRun(run_id=run.id, node_key="api", driver_key=driver, input_ref={"url": url})
    db.add(node)
    db.flush()
    job = ExecutionJob(
        project_id=project_id,
        kind="api",
        status="running",
        attempt=1,
        payload_json=json.dumps(
            {
                "run_id": run.id,
                "node_run_id": node.id,
                "driver": driver,
                "node_key": "api",
                "graph": graph,
            }
        ),
    )
    db.add(job)
    db.commit()
    return run, node, job


# ── 1. 无 Environment：Worker 入口必须 BLOCKED 且目标零请求 ──
def test_worker_blocks_run_without_environment_and_never_reaches_target(db_session, target_server):
    port = target_server
    run, node, job = _seed_job(db_session, url=f"http://127.0.0.1:{port}/data")

    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    job = db_session.get(ExecutionJob, job.id)

    assert result["status"] == "BLOCKED"
    assert node.status == "BLOCKED"
    assert node.error_class == "TARGET_POLICY_MISSING_BINDING"
    assert _CountingHandler.hits == 0, "策略未授权时不得发出任何请求"
    assert job.status == "failed"
    policy_snapshot = (node.output_ref or {})["policy"]
    assert policy_snapshot["decision"] == PolicyDecision.MISSING_BINDING.value
    assert policy_snapshot["reason_code"] == "RUN_ENVIRONMENT_MISSING"
    assert policy_snapshot["policy_hash"]
    events = [e.event_type for e in event_service.list_events(db_session, run.id)]
    assert "security.target_policy_missing_binding" in events


# ── 2. 有 Environment 但没有服务端 Policy：同样 BLOCKED ─────
def test_worker_blocks_run_without_policy_record(db_session, target_server):
    port = target_server
    env = _ensure_environment(db_session, base_url=f"http://127.0.0.1:{port}")
    run, node, job = _seed_job(
        db_session, url=f"http://127.0.0.1:{port}/data", environment_id=env.id
    )

    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)

    assert result["status"] == "BLOCKED"
    assert node.error_class == "TARGET_POLICY_MISSING_BINDING"
    assert (node.output_ref or {})["policy"]["reason_code"] == "NO_POLICY_CONFIGURED"
    # Environment.base_url 不是服务端策略，不能隐式放行。
    assert _CountingHandler.hits == 0


# ── 3. Policy Resolver 抛异常：UNAVAILABLE，不是放行 ────────
def test_worker_blocks_when_policy_resolver_raises(db_session, target_server, monkeypatch):
    port = target_server
    env = _ensure_environment(db_session, base_url=f"http://127.0.0.1:{port}")
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["127.0.0.1"], "allowed_ports": [port]},
    )
    run, node, job = _seed_job(
        db_session, url=f"http://127.0.0.1:{port}/data", environment_id=env.id
    )

    def _boom(self, **_kwargs):
        raise RuntimeError("policy store down")

    monkeypatch.setattr(
        "app.aiqe.security.target_policy.TargetPolicyResolver.resolve", _boom
    )
    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)

    assert result["status"] == "BLOCKED"
    assert node.error_class == "TARGET_POLICY_UNAVAILABLE"
    assert (node.output_ref or {})["policy"]["reason_code"] == "POLICY_RESOLVE_ERROR"
    assert _CountingHandler.hits == 0
    events = [e.event_type for e in event_service.list_events(db_session, run.id)]
    assert "security.target_policy_unavailable" in events


# ── 4. 策略记录在 claim 前被删除：BLOCKED ───────────────────
def test_worker_blocks_when_policy_record_removed_before_claim(db_session, target_server):
    port = target_server
    env = _ensure_environment(db_session, base_url=f"http://127.0.0.1:{port}")
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["127.0.0.1"], "allowed_ports": [port]},
    )
    run, node, job = _seed_job(
        db_session, url=f"http://127.0.0.1:{port}/data", environment_id=env.id
    )
    from app.aiqe.models.security import TargetPolicyRecord
    from sqlalchemy import delete

    db_session.execute(delete(TargetPolicyRecord))
    db_session.commit()

    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    assert result["status"] == "BLOCKED"
    assert node.error_class == "TARGET_POLICY_MISSING_BINDING"
    assert _CountingHandler.hits == 0


# ── 5. 策略过期：执行前必须重新解析，过期授权 BLOCKED ──────
def test_expired_policy_blocks_node_execution(db_session, target_server):
    port = target_server
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["127.0.0.1"], "allowed_ports": [port]},
    )
    from datetime import UTC, datetime, timedelta

    _, node, _ = _seed_job(db_session, url=f"http://127.0.0.1:{port}/data")
    expired = resolve_execution_policy(
        db_session, node.run, node, now=datetime.now(UTC) - timedelta(hours=1)
    )
    assert expired.decision is PolicyDecision.ALLOW
    assert expired.expires_at is not None and expired.expires_at < datetime.now(UTC)

    outcome = node_executor.execute_node(node, policy_context=expired)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class == "TARGET_POLICY_EXPIRED"
    assert _CountingHandler.hits == 0


# ── 6. 私网 / 元数据地址：即使 host 被显式列出也拒绝 ────────
@pytest.mark.parametrize(
    ("url", "host"),
    [
        ("http://127.0.0.1:{port}/", "127.0.0.1"),
        ("http://169.254.169.254/latest/meta-data/", "169.254.169.254"),
        ("http://10.0.0.5/admin", "10.0.0.5"),
        ("http://172.16.3.4/admin", "172.16.3.4"),
        ("http://192.168.1.9/admin", "192.168.1.9"),
        ("http://[::1]/", "::1"),
        ("http://[fe80::1]/", "fe80::1"),
    ],
)
def test_worker_blocks_private_and_metadata_targets(db_session, target_server, url, host):
    port = target_server
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": [host], "allowed_ports": [port, 80, 443]},
    )
    _, node, job = _seed_job(db_session, url=url.format(port=port))
    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)

    assert result["status"] == "BLOCKED", f"{url} 必须被拒绝"
    assert node.error_class in {
        "PRIVATE_ADDRESS_DENIED",
        "ADDRESS_BLOCKED",
        "TARGET_POLICY_DENIED",
    }
    assert _CountingHandler.hits == 0


# ── 7. 正向：显式授权后真实执行并落策略证据 ────────────────
def test_worker_allows_authorized_target_and_persists_policy_evidence(db_session, target_server):
    port = target_server
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [port],
            "allow_private_cidrs": ["127.0.0.0/8"],
            "max_redirects": 0,
        },
    )
    run, node, job = _seed_job(db_session, url=f"http://127.0.0.1:{port}/data")
    node.input_ref = {**node.input_ref, "expected_status": 200}
    db_session.commit()
    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)

    assert result["status"] == "PASSED", result
    assert _CountingHandler.hits == 1, "授权后应真实到达目标服务器一次"
    snapshot = (node.output_ref or {})["policy"]
    assert snapshot["decision"] == PolicyDecision.ALLOW.value
    assert snapshot["policy_version"] == 1
    assert snapshot["policy_hash"]
    assert snapshot["environment_id"] is None


# ── 8. DB：inline SQL / workflow query_registry 一律拒绝且零语句 ──
class _CountingResolver:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, ref):  # noqa: ANN001 - 与连接解析器签名一致
        self.calls += 1
        raise AssertionError("策略拒绝时不得解析数据库连接")


@pytest.mark.parametrize(
    "input_ref",
    [
        {"sql": "SELECT * FROM sys_user"},
        {"query_key": "q1", "sql": "SELECT 1"},
        {"query_key": "q1", "allowed_tables": ["sys_user"]},
        {"query_key": "q1", "query_registry": {"q1": "SELECT 1"}},
        {"query_key": "q1", "connection_url": "postgresql://evil/db"},
    ],
)
def test_db_node_rejects_workflow_sql_and_never_connects(
    db_session, monkeypatch, input_ref
):
    resolver = _CountingResolver()
    monkeypatch.setattr(node_executor, "default_connection_resolver", resolver)
    upsert_target_policy(
        db_session, project_id=1, environment_id=None, policy={"allowed_hosts": []}
    )
    _, node, job = _seed_job(db_session, url="", driver="db")
    node.input_ref = dict(input_ref)
    db_session.commit()

    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)

    assert result["status"] == "BLOCKED"
    assert node.error_class in {"INPUT_INVALID", "WORKFLOW_DB_OVERRIDE"}
    assert resolver.calls == 0, "被拒绝的 DB 节点不得建立任何数据库连接"


# ── 9. 四态决策模型 ──────────────────────────────────────────
def test_policy_decision_four_states(db_session):
    assert {item.value for item in PolicyDecision} == {
        "ALLOW",
        "DENY",
        "UNAVAILABLE",
        "MISSING_BINDING",
    }
    from app.aiqe.models.security import TargetPolicyRecord
    from sqlalchemy import delete

    # MISSING_BINDING：无 env、无策略
    _, node, _ = _seed_job(db_session, url="https://api.example.test/x")
    missing = resolve_execution_policy(db_session, node.run, node)
    assert missing.decision is PolicyDecision.MISSING_BINDING

    # UNAVAILABLE：没有 DB 会话
    unavailable = resolve_execution_policy(None, node.run, node)
    assert unavailable.decision is PolicyDecision.UNAVAILABLE

    # ALLOW：显式策略
    upsert_target_policy(
        db_session, project_id=1, environment_id=None, policy={"allowed_hosts": ["api.example.test"]}
    )
    allow = resolve_execution_policy(db_session, node.run, node)
    assert allow.decision is PolicyDecision.ALLOW
    assert allow.policy_id and allow.policy_hash and allow.expires_at

    # DENY：管理员显式拒绝
    db_session.execute(delete(TargetPolicyRecord))
    upsert_target_policy(
        db_session, project_id=1, environment_id=None, policy={"deny_all": True}
    )
    deny = resolve_execution_policy(db_session, node.run, node)
    assert deny.decision is PolicyDecision.DENY
    assert deny.reason_code == "EXPLICIT_DENY"


# ── 10. 静态门禁：旧执行器不得存在于 Worker 进程 ─────────────
def test_no_legacy_executors_and_policy_context_is_required():
    aiqe_root = Path(app.aiqe.__file__).resolve().parent
    offenders: list[str] = []
    for path in aiqe_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for banned in ("_execute_http(", "_execute_db(", "_has_target_policy"):
            if banned in text:
                offenders.append(f"{path.relative_to(aiqe_root)}:{banned}")
    assert offenders == [], f"正式执行链仍存在 legacy 调用: {offenders}"

    signature = inspect.signature(node_executor.execute_node)
    assert "policy_context" in signature.parameters
    param = signature.parameters["policy_context"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is inspect.Parameter.empty, "policy_context 不能有默认值（禁止隐式绕过）"

    # 纯本地节点必须显式声明能力，不能用 None 代表绕过。
    assert ExecutionCapabilities.NONE.network is False
    assert ExecutionCapabilities.NONE.db_read is False


# ── 11. 显式能力声明：网络节点不得借 NONE 绕过 ──────────────
def test_network_node_with_none_capabilities_blocks(db_session, target_server):
    port = target_server
    upsert_target_policy(
        db_session, project_id=1, environment_id=None, policy={"allowed_hosts": []}
    )
    _, node, _ = _seed_job(db_session, url=f"http://127.0.0.1:{port}/data")
    outcome = node_executor.execute_node(node, policy_context=ExecutionCapabilities.NONE)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class == "CAPABILITY_REQUIRED"
    assert _CountingHandler.hits == 0


# ── 12. 外部 Runner 正式入口：/payload 无策略必须 409，且不下发载荷 ──
def test_payload_endpoint_blocks_without_policy_and_never_handed_payload(
    client, db_session, target_server
):
    from app.services import ai_agent_service

    port = target_server
    _, node, job = _seed_job(db_session, url=f"http://127.0.0.1:{port}/data")
    _, plain = ai_agent_service.register_agent(
        db_session, "node-v16-payload", 1, ["api"], issue_token=True
    )
    assert plain
    resp = client.get(
        f"/api/v1/execution-jobs/{job.id}/payload",
        params={"node_id": "node-v16-payload"},
        headers={"X-AI-Agent-Token": plain},
    )
    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "TARGET_POLICY_MISSING_BINDING"
    assert detail["decision"] == "MISSING_BINDING"
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    assert node.status == "BLOCKED"
    assert _CountingHandler.hits == 0


def test_payload_endpoint_returns_policy_snapshot_when_authorized(
    client, db_session, target_server
):
    from app.services import ai_agent_service

    port = target_server
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
    _, node, job = _seed_job(db_session, url=f"http://127.0.0.1:{port}/data")
    _, plain = ai_agent_service.register_agent(
        db_session, "node-v16-payload-ok", 1, ["api"], issue_token=True
    )
    resp = client.get(
        f"/api/v1/execution-jobs/{job.id}/payload",
        params={"node_id": "node-v16-payload-ok"},
        headers={"X-AI-Agent-Token": plain},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()["data"]["payload"]
    assert payload["target_policy"]["decision"] == "ALLOW"
    assert payload["target_policy_hash"] == payload["target_policy"]["policy_hash"]
    assert payload["target_policy"]["policy_version"] == 1


# ── 13. 旧 Workflow 迁移标记：NEEDS_POLICY_REVIEW 禁止启动 ──
def test_workflow_needs_policy_review_cannot_launch(db_session):
    from app.aiqe.services.run_launch import LaunchError, launch_run
    from app.aiqe.services.workflow_service import approve_workflow, create_workflow

    _ensure_project(db_session, 1)
    graph = {
        "nodes": [
            {
                "key": "db",
                "driver": "db",
                "depends_on": [],
                "input": {"sql": "SELECT * FROM sys_user"},
            }
        ],
        "edges": [],
    }
    workflow = create_workflow(db_session, project_id=1, graph=graph)
    approve_workflow(db_session, workflow.id, approved_by=1)
    workflow.policy_status = "NEEDS_POLICY_REVIEW"
    db_session.commit()
    with pytest.raises(LaunchError) as excinfo:
        launch_run(
            db_session,
            project_id=1,
            user_id=1,
            workflow_definition_id=workflow.id,
            launch_key="v16-policy-review",
        )
    assert excinfo.value.code == "WORKFLOW_NEEDS_POLICY_REVIEW"


def test_legacy_workflow_migration_tool_classifies_workflows(tmp_path):
    """迁移工具：可映射 → MIGRATED；含 inline SQL → NEEDS_POLICY_REVIEW。"""
    import importlib.util

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "aiqe"
        / "migrate_workflow_target_policy.py"
    )
    spec = importlib.util.spec_from_file_location("v16_migration_tool", migration_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["v16_migration_tool"] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop("v16_migration_tool", None)
    from app.aiqe.models.workflow import WorkflowDefinition

    mappable = WorkflowDefinition(
        project_id=1,
        version=1,
        graph_json={
            "nodes": [
                {
                    "key": "api",
                    "driver": "http",
                    "input": {
                        "url": "https://api.example.test/orders",
                        "allowed_hosts": ["api.example.test"],
                        "allow_private": False,
                    },
                }
            ],
            "edges": [],
        },
        checksum="x",
    )
    analysis = module.analyze_workflow(mappable)
    assert analysis.status == "MIGRATED"
    assert analysis.hosts == {"api.example.test"}
    assert analysis.ports == {443}
    assert analysis.reasons == []

    unmappable = WorkflowDefinition(
        project_id=1,
        version=1,
        graph_json={
            "nodes": [
                {
                    "key": "db",
                    "driver": "db",
                    "input": {
                        "query_key": "q",
                        "sql": "SELECT * FROM sys_user",
                        "allowed_tables": ["sys_user"],
                    },
                }
            ],
            "edges": [],
        },
        checksum="y",
    )
    analysis = module.analyze_workflow(unmappable)
    assert analysis.status == "NEEDS_POLICY_REVIEW"
    assert any("db_node_requires_query_registry" in item for item in analysis.reasons)
    assert any("sql_requires_manual_migration" in item for item in analysis.reasons)

    private_only = WorkflowDefinition(
        project_id=1,
        version=1,
        graph_json={
            "nodes": [
                {
                    "key": "api",
                    "driver": "http",
                    "input": {"url": "http://10.0.0.5/x", "allow_private": True},
                }
            ],
            "edges": [],
        },
        checksum="z",
    )
    analysis = module.analyze_workflow(private_only)
    assert analysis.status == "NEEDS_POLICY_REVIEW"
    assert any("allow_private_requires_admin_cidrs" in item for item in analysis.reasons)
    # 私网目标已知，但不会自动生成 allow_private_cidrs
    assert module.analyze_workflow(private_only).allow_private_requested is True
