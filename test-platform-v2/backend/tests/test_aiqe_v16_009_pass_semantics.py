"""V16-009 验收：Assertion Engine 与 Run PASS 语义。

规格要求：
- BUSINESS 节点必须至少有一个有效业务 Oracle，Validate 阶段拒绝空断言；
- Driver 返回 200 但业务断言失败 → FAILED（Run 不得 PASS）；
- Driver 成功但无 Oracle → BLOCKED，Run 不得 PASS；
- Run PASSED 需要业务节点全部 PASSED 且存在 required assertion PASS；
- Setup/Cleanup/Observe 不能单独让 Run PASS。
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.aiqe.models.run import NodeRun, RunAssertionResult, TestRun
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.node_category import has_business_oracle, node_category
from app.aiqe.services.workflow_validator import WorkflowValidationError, validate_workflow
from app.models.execution_job import ExecutionJob
from app.models.project import Project

CALLS: list[str] = []


class _Handler(BaseHTTPRequestHandler):
    payload: dict = {"ok": True}

    def do_GET(self):  # noqa: N802
        CALLS.append(self.path)
        body = json.dumps(self.payload).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


@pytest.fixture()
def biz_server():
    CALLS.clear()
    _Handler.payload = {"ok": True}
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _ensure(db) -> None:
    if db.get(Project, 1) is None:
        db.add(Project(id=1, code="V16A", name="V16 Assert", owner_id=1, status=1))
        db.flush()
    register_manifest(
        db,
        node_id="v16-assert-http",
        driver_key="http",
        capabilities=["aiqe:http"],
        platforms=["linux"],
        evidence_ref="evidence://v16-assert",
    )


def _policy(db, port: int) -> None:
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


def _node_graph(port: int, *, assertions: list[dict] | None = None) -> dict:
    node = {
        "key": "biz",
        "driver": "http",
        "depends_on": [],
        "input": {
            "url": f"http://127.0.0.1:{port}/biz",
            "expected_status": 200,
        },
    }
    if assertions is not None:
        node["assertions"] = assertions
    return {"nodes": [node], "edges": []}


def _run_until_terminal(db, *, run_id: str, node_id: str, job_id: int, max_steps: int = 6) -> dict:
    """处理重试：同一节点失败后会被重新派发，直到节点终态。"""
    result: dict = {}
    job = job_id
    for _ in range(max_steps):
        result = job_consumer.run_job(db, job)
        db.expire_all()
        node = db.get(NodeRun, node_id)
        if node.status in {"PASSED", "FAILED", "BLOCKED", "ERROR", "CANCELED"}:
            return result
        next_job = (
            db.query(ExecutionJob)
            .filter(ExecutionJob.status == "pending")
            .order_by(ExecutionJob.id)
            .first()
        )
        if next_job is None:
            return result
        next_job.status = "running"
        db.commit()
        job = next_job.id
    return result


def _seed_job(db, *, port: int, assertions: list[dict] | None, input_ref: dict | None = None):
    _ensure(db)
    _policy(db, port)
    graph = _node_graph(port, assertions=assertions)
    run = TestRun(project_id=1, run_key="RUN-V16-A", status="RUNNING")
    db.add(run)
    db.flush()
    node_input = input_ref or graph["nodes"][0]["input"]
    node = NodeRun(
        run_id=run.id,
        node_key="biz",
        driver_key="http",
        input_ref=dict(node_input),
        assertions_json=list(assertions or []),
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
                "driver": "http",
                "node_key": "biz",
                "graph": graph,
            }
        ),
    )
    db.add(job)
    db.commit()
    return run, node, job


# ── 1. 节点类别与业务 Oracle ────────────────────────────────
def test_node_category_defaults_and_explicit_override():
    assert node_category({"driver": "http"}) == "BUSINESS"
    assert node_category({"driver": "http", "category": "setup"}) == "SETUP"
    assert node_category({"driver": "http", "type": "cleanup"}) == "CLEANUP"
    assert node_category({"driver": "http", "category": "observe"}) == "OBSERVE"
    assert node_category({"driver": "event"}) == "SETUP"


def test_business_oracle_detection():
    assert has_business_oracle([{"type": "http_status", "expected": 200}]) is True
    assert has_business_oracle([{"type": "exploratory"}]) is False
    assert has_business_oracle([], {"expected_status": 200}) is True
    assert has_business_oracle([], {"expect_text": "ok"}) is True
    assert has_business_oracle([], {}) is False


# ── 2. Workflow Validate：BUSINESS 空断言拒绝 ───────────────
def test_validator_rejects_business_node_without_oracle():
    graph = {
        "schema_version": "1.0",
        "nodes": [{"key": "biz", "driver": "http", "depends_on": [], "input": {"url": "https://a.test"}}],
        "edges": [],
    }
    with pytest.raises(WorkflowValidationError) as exc:
        validate_workflow(graph, registered_drivers={"http"})
    assert any(issue.code == "business_assertion_missing" for issue in exc.value.issues)


def test_validator_allows_setup_cleanup_observe_without_oracle():
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {"key": "prep", "driver": "http", "category": "setup", "depends_on": [], "input": {"url": "https://a.test"}},
            {"key": "obs", "driver": "http", "category": "observe", "depends_on": ["prep"], "input": {"url": "https://a.test"}},
            {"key": "biz", "driver": "http", "depends_on": ["obs"], "input": {"url": "https://a.test", "expected_status": 200}},
        ],
        "edges": [
            {"from": "prep", "to": "obs"},
            {"from": "obs", "to": "biz"},
        ],
    }
    validate_workflow(graph, registered_drivers={"http"})


# ── 3. Worker：Driver 200 但业务断言失败 → FAILED ───────────
def test_worker_business_assertion_failure_is_not_pass(db_session, biz_server):
    _Handler.payload = {"ok": False}
    assertions = [
        {
            "assertion_key": "ok_is_true",
            "oracle_layer": "REQ",
            "oracle_ref": "AC-BIZ-1",
            "type": "jsonpath",
            "path": "$.ok",
            "expected": True,
            "severity": "P0",
        }
    ]
    run, node, job = _seed_job(db_session, port=biz_server, assertions=assertions)
    result = _run_until_terminal(
        db_session, run_id=run.id, node_id=node.id, job_id=job.id
    )
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    run = db_session.get(TestRun, run.id)
    assert result["status"] == "FAILED", result
    assert node.status == "FAILED"
    assert run.status == "COMPLETED"
    assert run.outcome == "FAIL"
    assert CALLS and CALLS[0] == "/biz", "断言失败前必须真实执行 Driver"
    assert all(path == "/biz" for path in CALLS)


# ── 4. Worker：Driver 成功但无 Oracle → BLOCKED ─────────────
def test_worker_business_without_oracle_blocks(db_session, biz_server):
    run, node, job = _seed_job(
        db_session,
        port=biz_server,
        assertions=[],
        input_ref={"url": f"http://127.0.0.1:{biz_server}/biz"},
    )
    result = _run_until_terminal(
        db_session, run_id=run.id, node_id=node.id, job_id=job.id
    )
    db_session.expire_all()
    node = db_session.get(NodeRun, node.id)
    run = db_session.get(TestRun, run.id)
    assert result["status"] == "BLOCKED", result
    assert node.status == "BLOCKED"
    assert node.error_class == "NO_BUSINESS_ORACLE"
    assert run.outcome != "PASS"


# ── 5. Worker：合法业务断言 PASS → Run PASS ─────────────────
def test_worker_business_assertion_pass_yields_run_pass(db_session, biz_server):
    _Handler.payload = {"ok": True}
    assertions = [
        {
            "assertion_key": "ok_is_true",
            "oracle_layer": "REQ",
            "oracle_ref": "AC-BIZ-1",
            "type": "jsonpath",
            "path": "$.ok",
            "expected": True,
            "severity": "P0",
        }
    ]
    run, node, job = _seed_job(db_session, port=biz_server, assertions=assertions)
    result = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()
    run = db_session.get(TestRun, run.id)
    assert result["status"] == "PASSED", result
    assert run.status == "COMPLETED"
    assert run.outcome == "PASS"
    rows = list(
        db_session.query(RunAssertionResult)
        .filter(RunAssertionResult.status == "PASS")
        .all()
    )
    assert rows


# ── 6. Setup-only Run 不得 PASS；伪造 PASS 无断言也 INCOMPLETE ─
def test_setup_only_graph_cannot_pass(db_session):
    _ensure(db_session)
    run = TestRun(project_id=1, run_key="RUN-V16-A-SETUP", status="RUNNING")
    db_session.add(run)
    db_session.flush()
    graph = {
        "nodes": [{"key": "prep", "driver": "event", "category": "setup", "depends_on": []}],
        "edges": [],
    }
    dag_scheduler.create_node_runs(db_session, run.id, graph)
    dag_scheduler.complete_node(db_session, run.id, "prep", "PASSED", graph)
    db_session.refresh(run)
    assert run.status == "COMPLETED"
    assert run.outcome == "INCOMPLETE"
    events = [
        event.payload_json.get("business_gate")
        for event in __import__("app.aiqe.services.event_service", fromlist=["list_events"]).list_events(
            db_session, run.id
        )
        if event.event_type == "run.completed"
    ]
    assert "NO_BUSINESS_ORACLE" in events


def test_business_node_without_assertion_rows_never_passes(db_session):
    _ensure(db_session)
    run = TestRun(project_id=1, run_key="RUN-V16-A-FAKE", status="RUNNING")
    db_session.add(run)
    db_session.flush()
    graph = {
        "nodes": [{"key": "biz", "driver": "http", "depends_on": []}],
        "edges": [],
    }
    dag_scheduler.create_node_runs(db_session, run.id, graph)
    # 直接伪造节点 PASSED（没有任何 Assertion Result）
    dag_scheduler.complete_node(db_session, run.id, "biz", "PASSED", graph)
    db_session.refresh(run)
    assert run.status == "COMPLETED"
    assert run.outcome == "INCOMPLETE"
