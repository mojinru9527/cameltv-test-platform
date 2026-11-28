"""V16-017（R1）：平台链路真实 E2E（API/Launch → Worker → Driver → Assertion → Evidence）。

说明（诚实边界）：
- 本文件用**确定性本地 SUT fixture**（真实 HTTP 服务 + SQLite + 真实 Worker）验证 AIQE 平台链路，
  不是 CamelTv 真实业务租户/前端；产品级 TC-001/003/006/009/010 需要隔离 Test 环境，
  在 V16-017-R2 中标记 BLOCKED。
- 每个 TC 独立 fixture/数据隔离/业务断言/清理，运行 `pytest tests/e2e/aiqe/test_v16_017_platform_chain.py`。
"""
from __future__ import annotations

import json
import subprocess
import threading
import uuid
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest
from sqlalchemy import select

from app.aiqe.models.agent import AgentExecution
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.triage import TriageExperiment
from app.aiqe.models.tool import ToolExecutionAudit
from app.aiqe.security import upsert_target_policy
from app.aiqe.security.target_policy import PolicyDecision, TargetPolicy
from app.aiqe.services import job_consumer
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.agent_task_service import (
    approve_task,
    create_task,
    enqueue_task_job,
)
from app.aiqe.services.regression_service import (
    create_regression_request,
    record_deployment_attestation,
)
from app.aiqe.services.regression_terminal import handle_run_terminal
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.triage_service import (
    ExperimentError,
    create_experiment,
    launch_experiment,
    record_experiment_result,
    sync_experiment_result,
)
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.environment import Environment
from app.models.execution_job import ExecutionJob
from app.models.project import Project
from platform_results import pending_jobs, record_tc

pytestmark = pytest.mark.integration


class _Handler(BaseHTTPRequestHandler):
    orders: ClassVar[dict[str, Any]] = {}
    last_auth: ClassVar[str] = ""
    asset_hits: ClassVar[int] = 0
    #: 受控目标计数器：策略阻断必须表现为“目标实际收到 0 次请求”。
    health_hits: ClassVar[int] = 0
    # TC-008：模拟“修复后部署”——修复前 /fail 返回 success=false，修复后返回 true。
    fixed: ClassVar[bool] = False
    PAGE_HTML = """<!doctype html><html><head><title>AIQE-E2E</title></head><body>
<input id="name"/><button id="go" onclick="document.getElementById('out').textContent='hello '+document.getElementById('name').value">GO</button>
<div id="out">idle</div><img src="/pixel"/><img src="http://169.254.169.254/secret"/>
</body></html>"""
    canary_token: ClassVar[str] = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlMmUifQ.e2e-signature"
    )

    def log_message(self, *_args):
        return

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/page":
            body = self.PAGE_HTML.encode()
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/pixel":
            _Handler.asset_hits += 1
            self.send_response(200)
            self.send_header("content-type", "image/gif")
            self.send_header("content-length", "0")
            self.end_headers()
        elif self.path == "/echo":
            _Handler.last_auth = str(self.headers.get("authorization") or "")
            self._json({"received": True, "success": True})
        elif self.path == "/fail":
            self._json({"success": bool(_Handler.fixed)})
        elif self.path == "/health":
            _Handler.health_hits += 1
            self._json({"ok": True, "success": True})
        elif self.path.startswith("/orders/"):
            order = self.orders.get(self.path.rsplit("/", 1)[-1])
            self._json({"ok": bool(order), "success": bool(order), "order": order})
        else:
            self._json({"success": False}, 200)

    def do_POST(self):
        if self.path == "/login":
            self._json(
                {
                    "access_token": self.canary_token,
                    "refresh_token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJyZWZyZXNoIn0.e2e-refresh",
                    "success": True,
                }
            )
            return
        length = int(self.headers.get("content-length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        order = {"id": f"ORD-{len(self.orders) + 1}", **payload}
        self.orders[order["id"]] = order
        self._json({"success": True, "order": order}, 201)


@pytest.fixture()
def sut():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


def _repo_root() -> Path:
    """仓库根（backend/tests/e2e/aiqe → parents[4]）。"""
    return Path(__file__).resolve().parents[4]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    ).stdout.strip()


def _repo_commit_pair() -> tuple[str, str]:
    """取本次工作区的真实相邻提交（base, head）供 A5 ``read_git_diff`` 使用。

    不硬编码 SHA：CI/本地 checkout 的提交不同；没有 git 历史或 diff 为空时显式
    跳过（不是 PASS，也不能伪造 SHA）。
    """
    try:
        head = _git("rev-parse", "HEAD")
        base = _git("rev-parse", "HEAD~1")
        changed = _git("diff", "--name-only", f"{base}..{head}")
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"BLOCKED: 无法解析真实 git 提交对（{exc}）")
    if len(base) != 40 or len(head) != 40 or not changed:
        pytest.skip("BLOCKED: 当前 checkout 没有非空 diff 的相邻提交，无法证明 A5 真实 SHA 链路")
    return base, head


def _project_env(db, port: int) -> Environment:
    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="E2E", name="E2E", owner_id=1, status=1))
        db.flush()
    register_manifest(
        db,
        node_id="e2e-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://e2e-http",
    )
    env = Environment(
        project_id=1,
        name=f"e2e-{uuid.uuid4().hex[:6]}",
        base_url=f"http://127.0.0.1:{port}",
    )
    db.add(env)
    db.flush()
    upsert_target_policy(
        db,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [port],
            # 本地 SUT fixture 明确允许回环（服务端配置，客户端不可覆盖）
            "allow_private": True,
        },
    )
    db.commit()
    return env


def _drain(db) -> None:
    """只通过真实 Worker claim/lease 消费 Job；禁止把 pending Job 手工改成 running。"""
    for _ in range(50):
        claimed = job_consumer.claim_aiqe_jobs(db)
        if not claimed:
            break
        for job_id in claimed:
            job_consumer.run_job(db, job_id)
        db.commit()


def _launch(db, port: int, graph: dict) -> TestRun:
    env = _project_env(db, port)
    workflow = create_workflow(db, project_id=1, graph=graph)
    approve_workflow(db, workflow.id, approved_by=1)
    db.flush()
    run = launch_run(
        db,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        environment_id=env.id,
        launch_key=f"e2e-{uuid.uuid4().hex}",
    )
    db.commit()
    # Worker 轮询是异步语义：允许有限轮真实 claim（禁止人工把 pending 改成 running）。
    for _ in range(3):
        _drain(db)
        db.expire_all()
        run = db.get(TestRun, run.id)
        if not pending_jobs(db, run):
            break
    leftovers = pending_jobs(db, run)
    assert not leftovers, (
        "存在未被真实 Worker claim 的 pending Job（禁止人工 fallback 消费）: "
        f"{leftovers}；run={run.id}"
    )
    return run


def _http_graph(port: int, path: str, expected: Any, *, key: str = "biz") -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": key,
                "driver": "http",
                "depends_on": [],
                "input": {"url": f"http://127.0.0.1:{port}{path}", "expected_status": 200},
                "assertions": [
                    {
                        "assertion_key": f"{key}_business",
                        "oracle_layer": "REQ",
                        "oracle_ref": f"AC-{key.upper()}",
                        "type": "jsonpath",
                        "path": "$.success",
                        "expected": expected,
                        "severity": "P0",
                    }
                ],
            }
        ],
        "edges": [],
    }


def _assertions_of(db, run) -> list[Any]:
    from app.aiqe.models.run import RunAssertionResult, StepAttempt

    return list(
        db.scalars(
            select(RunAssertionResult)
            .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
            .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
            .where(NodeRun.run_id == run.id)
        )
    )


# ── TC-002：HTTP 200 但业务断言失败 ─────────────────────────
def test_tc_002_http_200_business_assertion_fails(db_session, sut):
    port = sut
    # /health 返回 success=true；用错 expected 制造业务失败
    run = _launch(
        db_session,
        port,
        _http_graph(port, "/health", expected=False),
    )
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assertions = _assertions_of(db_session, run)
    assert run.status == "COMPLETED"
    assert node.status == "FAILED", (node.status, node.error_class, [a.status for a in assertions])
    assert assertions and assertions[0].status == "FAIL", [a.status for a in assertions]
    assert run.outcome in {"FAIL", "INCOMPLETE"}, run.outcome
    record_tc("TC-PLATFORM-001", db_session, run)


# ── TC-004：DB 只读 + Query Registry ───────────────────────
def test_tc_004_query_registry_only_real_select(db_session, sut, tmp_path):
    import sqlite3

    from app.aiqe.services.query_registry import register_query

    target = tmp_path / "target.db"
    conn = sqlite3.connect(target)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, project_id INTEGER, status TEXT)")
    conn.execute("INSERT INTO orders VALUES (1, 1, 'paid')")
    conn.commit()
    conn.close()
    port = sut
    env = _project_env(db_session, port)
    register_manifest(
        db_session,
        node_id="e2e-db",
        driver_key="db",
        capabilities=["aiqe:db", "db.readonly"],
        platforms=["linux"],
        evidence_ref="evidence://e2e-db",
    )
    register_query(
        db_session,
        project_id=1,
        query_key="order_status",
        statement="SELECT id, status FROM orders WHERE project_id = :project_id AND id = :order_id",
        allowed_params=["project_id", "order_id"],
        allowed_tables=["orders"],
        connection_ref="e2e",
    )
    from sqlalchemy import create_engine

    from app.aiqe.services import node_executor

    engine = create_engine(f"sqlite:///{target.as_posix()}")
    node_executor.default_connection_resolver = lambda ref: engine  # type: ignore[assignment]
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "db",
                "driver": "db",
                "depends_on": [],
                "input": {"query_key": "order_status", "params": {"order_id": 1}},
                "assertions": [
                    {
                        "assertion_key": "row_count",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-DB",
                        "type": "db_row_count",
                        "expected": 1,
                        "severity": "P0",
                    }
                ],
            }
        ],
        "edges": [],
    }
    workflow = create_workflow(db_session, project_id=1, graph=graph)
    approve_workflow(db_session, workflow.id, approved_by=1)
    run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        environment_id=env.id,
        launch_key=f"e2e-db-{uuid.uuid4().hex}",
    )
    db_session.commit()
    _drain(db_session)
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert run.status == "COMPLETED", (run.status, run.preflight_json)
    assert run.outcome == "PASS", (run.outcome, node.status, node.error_class)
    from app.aiqe.models.run import RunAssertionResult

    rows = list(db_session.scalars(select(RunAssertionResult)))
    assert rows and rows[0].status == "PASS"
    assert not pending_jobs(db_session, run), pending_jobs(db_session, run)
    record_tc("TC-PLATFORM-002", db_session, run)


# ── TC-005：SSRF/云元数据零请求 ────────────────────────────
def test_tc_005_metadata_endpoint_never_reached(db_session, sut):
    port = sut
    graph = _http_graph(port, "/health", expected=True)
    graph["nodes"][0]["input"]["url"] = "http://169.254.169.254/latest/meta-data"
    run = _launch(db_session, port, graph)
    assert run.outcome != "PASS"
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "BLOCKED"
    error = node.error_class or ""
    assert any(token in error for token in ("POLICY", "TARGET", "PORT", "PRIVATE", "SSRF")), error
    from app.aiqe.services.event_service import list_events

    events = [event.event_type for event in list_events(db_session, run.id)]
    assert any(
        "target_policy" in item or "ssrf" in item or "policy" in item for item in events
    ), events
    # 受控目标证明：把“可真实到达但不在 allowlist”的服务端目标作为危险目标，
    # 策略必须阻断且目标计数器保持 0（而不是只断言节点状态）。
    _Handler.health_hits = 0
    denied_graph = _http_graph(port, "/health", expected=True)
    denied_graph["nodes"][0]["input"]["url"] = f"http://localhost:{port}/health"
    denied_run = _launch(db_session, port, denied_graph)
    denied_node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == denied_run.id))
    assert denied_node.status == "BLOCKED", denied_node.status
    assert _Handler.health_hits == 0, f"被阻断目标仍收到 {_Handler.health_hits} 次请求"
    record_tc(
        "TC-PLATFORM-003",
        db_session,
        run,
        status="BLOCKED",
        blocked_reason="策略阻断发生在断言执行前，无 AssertionResult（负向场景按 BLOCKED 记录）",
    )


# ── TC-007：迟到 fencing 结果拒绝 ─────────────────────────
def test_tc_007_stale_worker_result_rejected(db_session, sut):
    port = sut
    env = _project_env(db_session, port)
    graph = _http_graph(port, "/health", expected=True)
    workflow = create_workflow(db_session, project_id=1, graph=graph)
    approve_workflow(db_session, workflow.id, approved_by=1)
    _run = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        environment_id=env.id,
        launch_key=f"e2e-fence-{uuid.uuid4().hex}",
    )
    db_session.commit()
    claimed = job_consumer.claim_aiqe_jobs(db_session)
    assert claimed
    job = db_session.get(ExecutionJob, claimed[0])
    node = db_session.get(NodeRun, json.loads(job.payload_json)["node_run_id"])
    node.fencing_token = int(node.fencing_token or 0) + 5
    db_session.commit()
    result = job_consumer.complete_from_report(
        db_session,
        job_id=job.id,
        status="success",
        result={"status": "PASSED", "data": {"success": True}},
        fencing_token=1,
        node_id=job.node_id or "old-worker",
    )
    assert result.get("skipped") is True
    assert result.get("reason") in {"STALE_LEASE", "JOB_ALREADY_TERMINAL"}
    db_session.expire_all()
    assert db_session.get(NodeRun, node.id).status != "PASSED"


# ── TC-007：Worker 崩溃恢复（claim/执行/持久化/ack）+ 重复投递 ─────
def test_tc_007_worker_crash_recovery_and_duplicate_delivery(db_session, sut):
    """模拟 Worker 认领后崩溃（心跳/租约过期），必须由真实 Worker 重排完成。

    - 崩溃点：claim 之后、persist 之前（等价于 execute 中断）；
    - 崩溃后的迟到结果必须被 fencing 拒绝；
    - 恢复后同一 Run 重新 claim 完成，Assertion 只产出一份（重复投递幂等）。
    """
    from app.aiqe.services import dag_scheduler, reconciler

    port = sut
    env = _project_env(db_session, port)
    graph = _http_graph(port, "/health", expected=True)
    workflow = create_workflow(db_session, project_id=1, graph=graph)
    approve_workflow(db_session, workflow.id, approved_by=1)
    launched = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        environment_id=env.id,
        launch_key=f"e2e-crash-{uuid.uuid4().hex}",
    )
    db_session.commit()

    claimed = job_consumer.claim_aiqe_jobs(db_session)
    assert claimed, "首个 Job 必须可被真实 Worker 认领"
    job = db_session.get(ExecutionJob, claimed[0])
    node = db_session.get(NodeRun, json.loads(job.payload_json)["node_run_id"])
    stale_token = int(node.fencing_token or 0)
    assert node.status in {"RUNNING", "PENDING", "READY"}, node.status

    # 崩溃：claim 后不再心跳/执行 → 租约过期
    job.lease_expires_at = datetime.now(UTC) - timedelta(minutes=10)
    job.heartbeat_at = datetime.now(UTC) - timedelta(hours=2)
    db_session.commit()

    report = reconciler.reconcile(db_session, stale_seconds=60)
    db_session.commit()
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    assert job.id in report.expired_jobs, report
    assert node.status == "PENDING", (node.status, node.error_class)

    # 崩溃 Worker 的迟到结果：fencing 拒绝，且不改变节点状态
    late = job_consumer.complete_from_report(
        db_session,
        job_id=job.id,
        status="success",
        result={"status": "PASSED", "data": {"success": True}},
        fencing_token=stale_token,
        node_id="crashed-worker",
    )
    assert late.get("skipped") is True, late
    db_session.expire_all()
    assert db_session.get(NodeRun, node.id).status == "PENDING"

    # 恢复：PENDING → READY 后必须经调度器重新派发 Job（真实 dispatch 回调），
    # 再由真实 Worker 认领执行。
    from app.aiqe.services.execution_dispatcher import enqueue_node_run

    def _dispatch(row) -> None:
        enqueue_node_run(db_session, row, graph=graph)

    dag_scheduler.schedule(db_session, launched.id, graph, dispatch=_dispatch)
    db_session.commit()
    for _ in range(3):
        _drain(db_session)
        db_session.expire_all()
        run = db_session.get(TestRun, launched.id)
        if not pending_jobs(db_session, run):
            break
    run = db_session.get(TestRun, launched.id)
    assert not pending_jobs(db_session, run), pending_jobs(db_session, run)
    assert run.outcome == "PASS", (run.outcome, run.status, run.preflight_json)
    assertions = _assertions_of(db_session, run)
    assert assertions and all(item.status == "PASS" for item in assertions), [
        item.status for item in assertions
    ]
    assertion_count = len(assertions)

    # 重复投递：终态 Job 的重复上报必须被拒绝，且不新增 Assertion
    duplicate = job_consumer.complete_from_report(
        db_session,
        job_id=job.id,
        status="success",
        result={"status": "PASSED", "data": {"success": True}},
        fencing_token=stale_token,
        node_id="crashed-worker",
    )
    assert duplicate.get("skipped") is True, duplicate
    assert len(_assertions_of(db_session, run)) == assertion_count
    record_tc("TC-PLATFORM-004", db_session, run)


# ── TC-008：缺陷一键回归（真实 Launch/Worker/Scope/Comparison）────
def test_tc_008_defect_regression_end_to_end(db_session, sut):
    port = sut
    _Handler.fixed = False  # 修复前：/fail 返回 success=false
    env = _project_env(db_session, port)
    graph = _http_graph(port, "/fail", expected=True, key="biz")
    workflow = create_workflow(db_session, project_id=1, graph=graph)
    approve_workflow(db_session, workflow.id, approved_by=1)
    source = launch_run(
        db_session,
        project_id=1,
        user_id=1,
        workflow_definition_id=workflow.id,
        environment_id=env.id,
        launch_key=f"e2e-reg-src-{uuid.uuid4().hex}",
    )
    db_session.commit()
    _drain(db_session)
    db_session.expire_all()
    source = db_session.get(TestRun, source.id)
    assert source.outcome == "FAIL", source.outcome

    from app.models.defect import Defect, RunComparisonSnapshot

    defect = Defect(
        project_id=1, defect_id=f"BUG-E2E-{uuid.uuid4().hex[:6]}", title="x", severity="P1", status="open"
    )
    db_session.add(defect)
    db_session.flush()
    sha = "d" * 40
    # 模拟“修复后部署”：同一 SUT 在修复 SHA 下返回 success=true。
    _Handler.fixed = True
    record_deployment_attestation(
        db_session, project_id=1, environment_id=env.id, commit_sha=sha, source="ci"
    )
    db_session.commit()
    row, run, created = create_regression_request(
        db_session,
        project_id=1,
        defect_id=defect.id,
        fixed_sha=sha,
        target_environment_id=env.id,
        source_run_id=source.id,
        idempotency_key="e2e-reg-1",
    )
    db_session.commit()
    assert created is True and run is not None
    assert row.scope_snapshot_id
    from app.aiqe.models.regression_scope import RegressionScopeSnapshot

    scope = db_session.get(RegressionScopeSnapshot, row.scope_snapshot_id)
    assert "biz" in set(scope.mandatory_node_keys_json or [])
    _drain(db_session)
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    assert run.status in {"COMPLETED", "BLOCKED", "FAILED"}
    # 修复后回归必须真正 PASS；FAIL/BLOCKED/UNKNOWN 只能是测试失败，不可被接受为回归成功。
    assert run.outcome == "PASS", (run.outcome, run.status, run.preflight_json)
    result = handle_run_terminal(db_session, run_id=run.id)
    db_session.commit()
    assert result.status == "PASS", result.status
    assert result.comparison_id
    snapshot = db_session.get(RunComparisonSnapshot, result.comparison_id)
    assert snapshot is not None and snapshot.regression_run_id == run.id

    again, again_run, created_again = create_regression_request(
        db_session,
        project_id=1,
        defect_id=defect.id,
        fixed_sha=sha,
        target_environment_id=env.id,
        source_run_id=source.id,
        idempotency_key="e2e-reg-1",
    )
    db_session.commit()
    assert created_again is False and again.id == row.id
    assert again_run is not None and again_run.id == run.id
    record_tc("TC-PLATFORM-005", db_session, run)
    _Handler.fixed = False


# ── TC-010：A0 编排 + A1–A6 真实 Agent Adapter（ToolRegistry + Evidence）──
def test_tc_010_agent_task_platform_chain(db_session, sut, monkeypatch):
    """A0（run_plan 编排）→ A1..A6 全链路：正式 Worker 认领 + 真实工具审计。

    controlled_llm_test：LLM 为确定性 stub（模型调用是受控替换边界），
    本用例证明的是 AgentTask 生命周期/工具授权/审计/证据链，**不是**生产模型质量。

    链路（FIX-005）：
    AgentTask 记录 → 审批（approved_by/at）→ enqueue ExecutionJob →
    ``job_consumer.claim_agent_task_jobs`` 正式认领 → ``job_consumer.run_job`` 执行 →
    AgentExecution + ToolExecutionAudit → A5 ``read_git_diff`` 带真实 base/head SHA。

    真实：AgentTask 状态机、BoundToolRegistry 授权/审计、Evidence Resolver、
    AgentExecution 持久化、Worker 认领路径。
    边界：LLM stub（controlled_llm_test）；A6 仍需人工批准激活。
    """
    import json as _json

    from app.aiqe.services import agent_task_service

    port = sut
    run = _launch(db_session, port, _http_graph(port, "/health", expected=True))
    assert run.outcome == "PASS"
    base_sha, head_sha = _repo_commit_pair()

    task = create_task(
        db_session,
        project_id=1,
        goal="分析业务并准备测试、影响面与学习候选",
        include=(
            "a1_requirement",
            "a2_test_design",
            "a3_workflow",
            "a4_triage",
            "a5_impact",
            "a6_learning",
        ),
        requested_by=10,
        idempotency_key="e2e-agent-full",
        run_id=run.id,
        base_sha=base_sha,
        head_sha=head_sha,
    )
    assert agent_task_service.task_change_scope(task) == {
        "base_sha": base_sha,
        "head_sha": head_sha,
    }
    approve_task(db_session, task.id, project_id=1, approved_by=2)
    job = enqueue_task_job(db_session, task)
    db_session.commit()

    evidence_ref = f"run:{run.id}"
    prompts: list[str] = []

    def stub_llm(system: str, prompt: str) -> str:
        prompts.append(prompt)
        if "需求评估" in system:
            return _json.dumps(
                {
                    "summary": "健康检查需求可测",
                    "acceptance_criteria": [
                        {"id": "AC-1", "text": "health 返回 200", "source_ref": "PRD:health#200"}
                    ],
                    "risks": [],
                }
            )
        if "测试设计" in system:
            return _json.dumps(
                {
                    "decision": "approve",
                    "cases": [
                        {
                            "title": "health 200",
                            "priority": "P1",
                            "steps": ["GET /health"],
                            "acceptance_refs": ["AC-1"],
                        }
                    ],
                    "coverage_notes": "覆盖基本健康检查",
                    "reject_reason": "",
                    "duplicate_of": [],
                }
            )
        if "工作流规划" in system:
            workflow = _http_graph(port, "/health", expected=True)
            workflow["scenario_key"] = "e2e-a3"
            return _json.dumps(
                {
                    "workflow": workflow,
                    "rationale": "最小可执行工作流",
                    "approval_required": True,
                    "approval_status": "pending",
                }
            )
        if "变更影响" in system:
            return _json.dumps(
                {
                    "impacted_areas": ["unknown"],
                    "candidate_suites": ["smoke-suite"],
                    "forced_suites": [],
                    "rationale": "无结构性证据时扩大回归",
                }
            )
        if "归因" in system:
            return _json.dumps(
                {
                    "execution_outcome": "INCOMPLETE",
                    "attribution_status": "NEEDS_EXPERIMENT",
                    "hypotheses": [
                        {
                            "classification": "AUTOMATION",
                            "summary": "Runner 环境导致节点未完成",
                            "supporting_evidence": [evidence_ref],
                            "contradicting_evidence": [],
                            "missing_evidence": ["runner 日志"],
                            "recommended_experiment": "E1",
                            "confidence": None,
                            "confidence_band": "LOW",
                            "status": "PROPOSED",
                        }
                    ],
                    "human_review_required": True,
                    "auto_close_defect": False,
                }
            )
        if "BugPattern" in system:
            return _json.dumps(
                {
                    "pattern_key": "runner-environment-flake",
                    "description": "Runner 环境不稳定导致节点未完成",
                    "conditions": ["node INCOMPLETE"],
                    "source_refs": [evidence_ref],
                    "false_positive_risk": "LOW",
                    "rationale": "来自真实 Run 失败证据",
                }
            )
        raise AssertionError(f"未覆盖的 Agent system prompt: {system[:80]}")

    # controlled_llm_test：只在模型调用边界注入 stub；工具/授权/审计全部真实执行。
    monkeypatch.setattr(
        agent_task_service, "resolve_project_llm", lambda db, project_id: stub_llm
    )
    claimed = job_consumer.claim_agent_task_jobs(db_session)
    assert claimed == [job.id], f"Worker 必须经正式 claim 认领 AgentTask Job: {claimed}"
    result = job_consumer.run_job(db_session, job.id)
    db_session.commit()
    assert result["task"]["status"] == "COMPLETED", result
    executions = list(
        db_session.scalars(
            select(AgentExecution)
            .where(AgentExecution.parent_task_id == task.id)
            .order_by(AgentExecution.created_at)
        )
    )
    keys = {item.agent_key for item in executions}
    assert keys == {"A1", "A2", "A3", "A4", "A5", "A6"}, keys
    assert all(item.task_id for item in executions), "每个 AgentExecution 必须绑定 plan 节点"
    # 每个 Agent 的真实工具调用必须与 ToolExecutionAudit 对账
    declared = {
        item.agent_key: {call.get("tool") for call in (item.tool_calls_json or [])}
        for item in executions
    }
    assert "read_requirements" in declared["A1"]
    assert "read_git_diff" in declared["A5"], "A5 必须用受控工具读取服务端 diff"
    assert "read_defects" in declared["A4"]
    assert "read_defects" in declared["A6"]
    audits = list(db_session.scalars(select(ToolExecutionAudit)))
    assert audits and all(row.task_id == task.id for row in audits)
    audit_tools = {row.tool_name for row in audits}
    assert {"read_project_context", "read_requirements", "read_defects"}.issubset(audit_tools)
    # FIX-005：ToolExecutionAudit 必须记录 read_git_diff 且参数是本次任务的真实 SHA。
    git_diff_audits = [
        row for row in audits if row.tool_name == "read_git_diff" and row.decision == "ALLOW"
    ]
    assert git_diff_audits, [(row.tool_name, row.decision, row.reason) for row in audits]
    for audit in git_diff_audits:
        summary = dict(audit.args_summary_json or {})
        assert summary.get("base_sha") == base_sha, summary
        assert summary.get("head_sha") == head_sha, summary
        assert audit.agent_key == "A5"
        assert audit.actor_id is None or int(audit.actor_id) >= 0
    # 写工具仍未开放：不得出现 create_draft/create_learning_candidate 的 ALLOW 审计
    assert not {
        row.tool_name
        for row in audits
        if row.decision == "ALLOW"
        and row.tool_name in {"create_draft", "create_learning_candidate"}
    }
    # A4/A6 的证据引用必须经服务端 Evidence Resolver（而非模型自述）
    assert evidence_ref in _json.dumps([row.source_refs_json for row in executions])
    available = {row.tool_name for row in audits}
    benchmark_tools = {"read_benchmark_dataset"} & available
    assert benchmark_tools == set()
    job_row = db_session.get(ExecutionJob, job.id)
    assert job_row.status == "success"
    assert job_row.attempt >= 1
    record_tc(
        "TC-PLATFORM-009",
        db_session,
        run,
        status="PASS",
        blocked_reason="",
    )


# ── TC-006：Secret 全链路（输出 Handle/下游授权/明文零落库）────
def test_tc_006_secret_chain_no_plaintext(db_session, sut):
    import json as _json

    from sqlalchemy import select

    from app.aiqe.models.event import RunEvent
    from app.aiqe.models.run import StepAttempt
    from app.aiqe.models.secret_handle import SecretHandle
    from app.aiqe.services.secret_vault import SecretAccessDenied, resolve_secret_handle

    port = sut
    _Handler.last_auth = ""
    token_value = _Handler.canary_token
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "login",
                "driver": "http",
                "depends_on": [],
                "input": {
                    "url": f"http://127.0.0.1:{port}/login",
                    "method": "POST",
                    "json": {"username": "qa", "password": "not-a-secret"},
                    "expected_status": 200,
                },
                "outputs": {"token": "$.json.access_token"},
                "output_schema": {
                    "type": "object",
                    "properties": {"token": {"type": "string", "sensitive": True}},
                },
                "assertions": [
                    {
                        "assertion_key": "login_http",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-LOGIN-200",
                        "type": "http_status",
                        "expected": 200,
                        "severity": "P0",
                    }
                ],
            },
            {
                "key": "use",
                "driver": "http",
                "depends_on": ["login"],
                "input": {
                    "url": f"http://127.0.0.1:{port}/echo",
                    "headers": {"Authorization": "Bearer ${nodes.login.outputs.token}"},
                    "expected_status": 200,
                },
                "assertions": [
                    {
                        "assertion_key": "echo_received",
                        "oracle_layer": "REQ",
                        "oracle_ref": "AC-ECHO",
                        "type": "jsonpath",
                        "path": "$.received",
                        "expected": True,
                        "severity": "P0",
                    }
                ],
            },
        ],
        "edges": [{"from": "login", "to": "use"}],
    }
    run = _launch(db_session, port, graph)
    nodes_debug = [
        (n.node_key, n.status, n.error_class, n.output_ref, n.outputs_json)
        for n in db_session.scalars(select(NodeRun).where(NodeRun.run_id == run.id))
    ]
    assert run.outcome == "PASS", (run.outcome, run.status, nodes_debug, run.preflight_json)
    # 下游真实收到 Canary 明文（证明 Handle 被授权解析）
    assert _Handler.last_auth == f"Bearer {token_value}"

    handles = list(
        db_session.scalars(
            select(SecretHandle).order_by(SecretHandle.created_at, SecretHandle.id)
        )
    )
    assert handles, "登录输出必须生成 SecretHandle"
    handle = next(
        (
            item
            for item in handles
            if "use" in list((item.consumer_scope_json or {}).get("allowed_nodes") or [])
        ),
        handles[0],
    )
    scope = handle.consumer_scope_json or {}
    assert "use" in list(scope.get("allowed_nodes") or []), [
        (item.id, item.consumer_scope_json) for item in handles
    ]
    # 越权解析必须拒绝
    with pytest.raises(SecretAccessDenied):
        resolve_secret_handle(
            db_session,
            handle_id=handle.id,
            run_id=run.id,
            consumer_node_key="other-node",
            project_id=int(run.project_id),
        )

    # 明文零落库：输出/Job/事件/Handle 序列化均不得出现 Canary
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    login_node = db_session.scalar(
        select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.node_key == "login")
    )
    payloads = [
        _json.dumps(login_node.outputs_json, ensure_ascii=False),
        _json.dumps(login_node.output_ref, ensure_ascii=False),
        _json.dumps(handle.__dict__, default=str),
        _json.dumps(run.environment_snapshot_json, ensure_ascii=False, default=str),
    ]
    for job in db_session.scalars(select(ExecutionJob).where(ExecutionJob.run_id == run.id)):
        payloads.append(job.payload_json or "")
        payloads.append(job.result_json or "")
    for event in db_session.scalars(select(RunEvent).where(RunEvent.run_id == run.id)):
        payloads.append(_json.dumps(event.payload_json, ensure_ascii=False))
    for attempt in db_session.scalars(
        select(StepAttempt).join(NodeRun, NodeRun.id == StepAttempt.node_run_id).where(
            NodeRun.run_id == run.id
        )
    ):
        payloads.append(_json.dumps(attempt.output_summary_json, ensure_ascii=False, default=str))
    assert node is not None
    for payload in payloads:
        assert token_value not in payload
        assert "e2e-refresh" not in payload
    record_tc("TC-PLATFORM-006", db_session, run)


# ── TC-009：Noise E1–E6 单变量实验（真实 Run/Worker）────────
def test_tc_009_noise_experiments_e1_to_e6(db_session, sut):
    port = sut
    baseline = _launch(
        db_session,
        port,
        _http_graph(port, "/health", expected=True, key="biz"),
    )
    assert baseline.outcome == "PASS"
    specs = [
        ("E1", "run_attempt", 2),
        ("E2", "fixture_namespace", "e2e-ns-2"),
        ("E3", "upstream_mode", "recorded"),
        ("E4", "feature_flag", "overlay=on"),
        ("E5", "worker_instance", "e2e-worker-2"),
        ("E6", "network_profile", "3g-lossy"),
    ]
    launched_runs: list[str] = []
    for key, variable, value in specs:
        exp = create_experiment(
            db_session,
            experiment_key=key,
            idempotency_key=f"e2e-{key}-{uuid.uuid4().hex[:6]}",
            baseline_run_id=baseline.id,
            change={variable: value},
        )
        db_session.commit()
        launched = launch_experiment(db_session, exp.id)
        db_session.commit()
        _drain(db_session)
        db_session.expire_all()
        exp = db_session.get(TriageExperiment, exp.id)
        exp = sync_experiment_result(db_session, exp.id)
        db_session.commit()
        run = db_session.get(TestRun, launched.verification_run_id)
        assert run is not None and run.retest_of == baseline.id
        assert run.source_type == "experiment"
        assert run.status in {"COMPLETED", "BLOCKED", "FAILED"}, (key, run.status)
        assert exp.changed_dimension == variable, (key, exp.changed_dimension)
        assert exp.status in {"COMPLETED", "FAILED", "UNKNOWN", "BLOCKED"}, (
            key,
            exp.status,
            exp.error_code,
        )
        # 故障归因：只有终态 Run 才能给出结论；UNKNOWN 不得被归类成已知根因。
        if exp.status == "COMPLETED" and run.outcome:
            conclusion = "REFUTED" if run.outcome == "PASS" else "SUPPORTED"
            record_experiment_result(db_session, exp.id, result=conclusion)
            db_session.commit()
            assert db_session.get(TriageExperiment, exp.id).experiment_result == conclusion
        else:
            with pytest.raises(ExperimentError):
                record_experiment_result(db_session, exp.id, result="SUPPORTED")
        assert exp.snapshot_diff_json["single_variable"] is True, key
        assert exp.snapshot_diff_json["expected_dimension"] == variable, key
        launched_runs.append(run.id)
    assert len(set(launched_runs)) == 6
    record_tc("TC-PLATFORM-007", db_session, baseline)


# ── TC-003：真实 Chromium 交互 + 子资源安全拦截 ─────────────
@pytest.mark.browser
def test_tc_003_browser_interaction_and_interception(db_session, sut):
    """浏览器节点必须经 ``node_executor``（正式节点执行器）而不是直接构造 Driver。

    平台约束：进程内 Worker 不消费 browser driver（``job_consumer.INPROCESS_DRIVERS``
    只含 http/db），浏览器节点由外部 Runner 执行。本用例覆盖
    ``node_executor.execute_node -> _execute_playwright -> PlaywrightDriver`` 的
    策略注入与拦截链路；完整 Run→Job→外部 Worker 链路见 V16-017-R1 缺口记录。
    """
    from app.aiqe.models.run import NodeRun

    from app.aiqe.services import node_executor

    port = sut
    _Handler.asset_hits = 0
    policy = TargetPolicy(
        project_id=1,
        version=1,
        source="policy_record:e2e",
        allowed_hosts=("127.0.0.1",),
        allowed_ports=(port,),
        allow_private_cidrs=("127.0.0.0/8",),
        max_redirects=0,
        decision=PolicyDecision.ALLOW,
    )
    node = NodeRun(
        run_id="transient-e2e-browser",
        node_key="browser",
        driver_key="playwright",
        status="running",
        input_ref={
            "url": f"http://127.0.0.1:{port}/page",
            "actions": [
                {"type": "fill", "selector": "#name", "value": "Camel"},
                {"type": "click", "selector": "#go"},
                {"type": "assert_text", "selector": "#out", "expected": "hello Camel"},
            ],
        },
    )
    result = node_executor.execute_node(node, policy_context=policy)
    assert result.status == "PASSED", (result.error_class, result.detail)
    data = result.data or {}
    assert data.get("title") == "AIQE-E2E", data
    records = data.get("actions") or []
    assert len(records) >= 3 and all(not item.get("error") for item in records), records
    assert records[-1]["action"] == "assert_text"
    assert records[-1]["text"].strip() == "hello Camel"
    assert _Handler.asset_hits >= 1, "允许的子资源必须真实请求"
    codes = {item["code"] for item in data.get("security_denials") or []}
    assert codes & {
        "ADDRESS_BLOCKED",
        "PRIVATE_ADDRESS_DENIED",
        "HOST_NOT_ALLOWED",
        "PORT_NOT_ALLOWED",
    }, codes
    assert any(
        item.get("host") == "169.254.169.254" for item in data.get("security_denials") or []
    ), data.get("security_denials")
    record_tc(
        "TC-PLATFORM-008",
        status="BLOCKED",
        blocked_reason=(
            "browser 节点由外部 Runner 执行；本用例覆盖 node_executor→PlaywrightDriver，"
            "未产生 TestRun，故不计入运行证据索引 PASS"
        ),
    )
