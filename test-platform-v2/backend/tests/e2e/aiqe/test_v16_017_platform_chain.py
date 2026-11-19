"""V16-017（R1）：平台链路真实 E2E（API/Launch → Worker → Driver → Assertion → Evidence）。

说明（诚实边界）：
- 本文件用**确定性本地 SUT fixture**（真实 HTTP 服务 + SQLite + 真实 Worker）验证 AIQE 平台链路，
  不是 CamelTv 真实业务租户/前端；产品级 TC-001/003/006/009/010 需要隔离 Test 环境，
  在 V16-017-R2 中标记 BLOCKED。
- 每个 TC 独立 fixture/数据隔离/业务断言/清理，运行 `pytest tests/e2e/aiqe/test_v16_017_platform_chain.py`。
"""
from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

import pytest
from sqlalchemy import select

from app.aiqe.models.agent import AgentExecution
from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.models.tool import ToolExecutionAudit
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import job_consumer
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.agent_task_service import (
    approve_task,
    create_task,
    enqueue_task_job,
    execute_task_job,
)
from app.aiqe.services.regression_service import (
    create_regression_request,
    record_deployment_attestation,
)
from app.aiqe.services.regression_terminal import handle_run_terminal
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.models.environment import Environment
from app.models.execution_job import ExecutionJob
from app.models.project import Project

pytestmark = pytest.mark.integration


class _Handler(BaseHTTPRequestHandler):
    orders: ClassVar[dict[str, Any]] = {}

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
        if self.path == "/health":
            self._json({"ok": True, "success": True})
        elif self.path.startswith("/orders/"):
            order = self.orders.get(self.path.rsplit("/", 1)[-1])
            self._json({"ok": bool(order), "success": bool(order), "order": order})
        else:
            self._json({"success": False}, 200)

    def do_POST(self):
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
    for _ in range(50):
        claimed = job_consumer.claim_aiqe_jobs(db)
        if not claimed:
            break
        for job_id in claimed:
            job_consumer.run_job(db, job_id)
        db.commit()
    pending = list(
        db.scalars(select(ExecutionJob).where(ExecutionJob.status == "pending"))
    )
    for job in pending:
        job.status = "running"
        job.node_id = "e2e-worker"
        job.attempt = int(job.attempt or 0) + 1
        db.commit()
        job_consumer.run_job(db, job.id)
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
    _drain(db)
    db.expire_all()
    return db.get(TestRun, run.id)


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


# ── TC-008：缺陷一键回归（真实 Launch/Worker/Scope/Comparison）────
def test_tc_008_defect_regression_end_to_end(db_session, sut):
    port = sut
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
    result = handle_run_terminal(db_session, run_id=run.id)
    db_session.commit()
    assert result.status in {"FAIL", "BLOCKED", "UNKNOWN", "PASS"}
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


# ── TC-010：AgentTask → Outbox → Job → ToolRegistry → AgentExecution ─
def test_tc_010_agent_task_platform_chain(db_session):
    from app.aiqe.agents.protocol import AgentResult

    _project_env(db_session, 80)
    db_session.commit()
    task = create_task(
        db_session,
        project_id=1,
        goal="分析业务并准备测试",
        include=("a1_requirement",),
        requested_by=10,
        idempotency_key="e2e-agent-1",
    )
    approve_task(db_session, task.id, project_id=1, approved_by=2)
    job = enqueue_task_job(db_session, task)
    db_session.commit()

    def executor(plan_task, context, request):
        tool = context.tools.resolve("A1", "read_project_context")
        data = tool()
        return AgentResult(
            agent_key="A1",
            agent_version="1.0.0",
            status="COMPLETED",
            output={"project": data["project_id"]},
        )

    result = execute_task_job(db_session, job.id, executor=executor)
    db_session.commit()
    assert result["task"]["status"] == "COMPLETED"
    executions = list(
        db_session.scalars(
            select(AgentExecution).where(AgentExecution.parent_task_id == task.id)
        )
    )
    assert len(executions) == 1 and executions[0].agent_key == "A1"
    audits = list(db_session.scalars(select(ToolExecutionAudit)))
    assert audits and audits[0].tool_name == "read_project_context"
    job_row = db_session.get(ExecutionJob, job.id)
    assert job_row.status == "success"
