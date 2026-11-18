"""AUD-007：Assertion Engine 完整化验收测试。

对应 v1.5 §01 AUD-007「验收」：
- HTTP 200 + ``business_code=4001``，预期 0：FAIL；
- JSONPath 字段缺失：FAIL 或 UNKNOWN，不能 PASS；
- Schema 多字段类型错误：FAIL 并定位 JSON Pointer；
- P0 没有 Oracle：BLOCKED；
- evaluator 抛异常：ERROR，不伪装产品 FAIL；
- Gate 只读取 Required Assertion；Driver ``status=success`` 不直接转化为 Case PASS。
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import select

from app.aiqe.assertions import (
    BLOCKED,
    ERROR,
    FAIL,
    NOT_EVALUATED,
    PASS,
    UNKNOWN,
    AssertionOutcome,
    Observation,
    OracleRegistry,
    aggregate,
    evaluate_all,
    evaluate_assertion,
    known_operators,
    poll_until,
    resolve_json_path,
)
from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.security import SafeHttpResult, upsert_target_policy
from app.aiqe.services import dag_scheduler, job_consumer
from app.aiqe.services.execution_dispatcher import enqueue_node_run
from app.models.execution_job import ExecutionJob

OBS = Observation.from_http(
    status_code=200,
    headers={"content-type": "application/json"},
    duration_ms=12,
    text=json.dumps(
        {
            "code": 4001,
            "message": "insufficient stock",
            "data": {"status": "live", "order_id": "o-1", "items": [{"qty": "two"}]},
        }
    ),
)


# ── 1. 算子与 JSONPath ────────────────────────────────────
def test_json_path_subset():
    assert resolve_json_path({"a": {"b": 1}}, "$.a.b") == (True, 1)
    assert resolve_json_path({"a": [10, 20]}, "$.a[1]") == (True, 20)
    assert resolve_json_path({"a": {"b": 1}}, "a.b") == (True, 1)
    assert resolve_json_path({"a": 1}, "$.missing") == (False, None)
    assert resolve_json_path({"a": 1}, "$.a.b") == (False, None)


def test_operators_registered():
    expected = {
        "equals",
        "not_equals",
        "contains",
        "not_contains",
        "exists",
        "not_exists",
        "regex",
        "json_schema",
        "gte",
        "lte",
        "in",
    }
    assert expected <= known_operators()


@pytest.mark.parametrize(
    ("spec", "status"),
    [
        ({"operator": "equals", "source": "http_status", "expected": 200}, PASS),
        ({"operator": "equals", "source": "http_body", "path": "$.code", "expected": 0}, FAIL),
        ({"operator": "equals", "source": "http_body", "path": "$.code", "expected": 4001}, PASS),
        ({"operator": "contains", "source": "http_body", "path": "$.message", "expected": "stock"}, PASS),
        ({"operator": "regex", "source": "http_body", "path": "$.data.order_id", "expected": r"^o-\d+$"}, PASS),
        ({"operator": "exists", "source": "http_body", "path": "$.data.order_id", "expected": True}, PASS),
        ({"operator": "exists", "source": "http_body", "path": "$.data.missing", "expected": True}, FAIL),
        ({"operator": "not_exists", "source": "http_body", "path": "$.data.missing"}, PASS),
        ({"operator": "in", "source": "http_body", "path": "$.data.status", "expected": ["live", "draft"]}, PASS),
        ({"operator": "gte", "source": "timing", "path": "duration_ms", "expected": 0}, PASS),
        ({"operator": "equals", "source": "http_header", "path": "Content-Type", "expected": "application/json"}, PASS),
    ],
)
def test_operator_semantics(spec, status):
    outcome = evaluate_assertion({**spec, "assertion_key": "k1"}, OBS)
    assert outcome.status == status, outcome


def test_json_schema_reports_pointer():
    schema = {
        "type": "object",
        "required": ["code"],
        "properties": {
            "data": {
                "type": "object",
                "properties": {"items": {"type": "array", "items": {"type": "object"}}},
            },
            "code": {"type": "integer"},
        },
    }
    outcome = evaluate_assertion(
        {"operator": "json_schema", "source": "http_body", "expected": schema}, OBS
    )
    assert outcome.status == PASS

    bad_schema = {
        "type": "object",
        "properties": {"data": {"type": "object", "properties": {"status": {"type": "integer"}}}},
    }
    outcome = evaluate_assertion(
        {"operator": "json_schema", "source": "http_body", "expected": bad_schema}, OBS
    )
    assert outcome.status == FAIL
    assert any("/data/status" in error for error in outcome.detail["errors"])


# ── 2. 缺失值 / Oracle / 异常 ─────────────────────────────
def test_missing_value_never_passes():
    required = evaluate_assertion(
        {"assertion_key": "m1", "operator": "equals", "source": "http_body", "path": "$.nope"},
        OBS,
    )
    assert required.status == FAIL

    optional = evaluate_assertion(
        {
            "assertion_key": "m2",
            "operator": "equals",
            "source": "http_body",
            "path": "$.nope",
            "required": False,
        },
        OBS,
    )
    assert optional.status == UNKNOWN


def test_p0_without_oracle_blocked():
    outcome = evaluate_assertion(
        {"assertion_key": "p0", "operator": "equals", "source": "http_status", "expected": 200, "severity": "P0"},
        OBS,
    )
    assert outcome.status == BLOCKED
    assert outcome.detail["reason"] == "ORACLE_MISSING"


def test_p0_with_unapproved_oracle_blocked():
    outcome = evaluate_assertion(
        {
            "assertion_key": "p0",
            "operator": "equals",
            "source": "http_status",
            "expected": 200,
            "severity": "P0",
            "oracle_ref": {"type": "requirement_ac", "id": "AC-1", "revision": 3},
        },
        OBS,
        oracle_registry=OracleRegistry(["requirement_ac:AC-2"]),
    )
    assert outcome.status == BLOCKED
    assert outcome.detail["reason"] == "ORACLE_NOT_APPROVED"


def test_p0_with_approved_oracle_evaluates():
    outcome = evaluate_assertion(
        {
            "assertion_key": "p0",
            "operator": "equals",
            "source": "http_status",
            "expected": 200,
            "severity": "P0",
            "oracle_ref": {"type": "requirement_ac", "id": "AC-1", "revision": 3},
        },
        OBS,
        oracle_registry=OracleRegistry(["requirement_ac:AC-1"]),
    )
    assert outcome.status == PASS
    assert outcome.oracle_id == "AC-1"
    assert outcome.oracle_revision == 3


def test_evaluator_exception_is_error_not_fail():
    unknown_operator = evaluate_assertion(
        {"assertion_key": "e1", "operator": "teleport", "source": "http_status"}, OBS
    )
    assert unknown_operator.status == ERROR
    assert unknown_operator.detail["reason"] == "OPERATOR_ERROR"

    bad_regex = evaluate_assertion(
        {"assertion_key": "e2", "operator": "regex", "source": "http_body", "path": "$.code", "expected": "("},
        OBS,
    )
    assert bad_regex.status == ERROR


def test_driver_error_yields_not_evaluated():
    failed = Observation.from_http(status_code=None, error="TIMEOUT")
    outcome = evaluate_assertion(
        {"assertion_key": "d1", "operator": "equals", "source": "http_status", "expected": 200},
        failed,
    )
    assert outcome.status == NOT_EVALUATED


# ── 3. 聚合 ──────────────────────────────────────────────
def test_aggregate_priority():
    def make(status, required=True):
        return AssertionOutcome(
            assertion_key=f"k-{status}-{required}",
            status=status,
            operator="equals",
            source="http_status",
            source_ref="http_status",
            required=required,
        )

    assert aggregate([make(PASS), make(PASS)]) == PASS
    assert aggregate([make(PASS), make(FAIL)]) == FAIL
    assert aggregate([make(PASS), make(FAIL, required=False)]) == PASS
    assert aggregate([make(BLOCKED), make(FAIL)]) == BLOCKED
    assert aggregate([make(ERROR), make(FAIL)]) == ERROR
    assert aggregate([make(UNKNOWN), make(PASS)]) == UNKNOWN
    assert aggregate([]) == NOT_EVALUATED


def test_poll_until_records_samples_and_stops():
    import time

    calls = {"n": 0}

    def evaluate():
        calls["n"] += 1
        status = PASS if calls["n"] >= 3 else UNKNOWN
        return evaluate_assertion(
            {"assertion_key": "poll", "operator": "equals", "source": "http_status", "expected": 200},
            Observation.from_http(status_code=200 if status == PASS else None, error=None if status == PASS else "PENDING"),
        )

    outcome, samples = poll_until(evaluate, timeout_ms=1000, interval_ms=1, sleep=lambda _s: time.sleep(0))
    assert outcome.status == PASS
    assert len(samples) == 3


# ── 4. 端到端：HTTP 200 + 业务错误 → FAIL + 落库 ─────────────
class _StubHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = json.dumps({"code": 4001, "message": "insufficient stock"}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


@pytest.fixture()
def stub_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _seed(db, *, port: int, assertions: list[dict], key: str = "RUN-AUD007") -> tuple[TestRun, ExecutionJob]:
    upsert_target_policy(
        db,
        project_id=1,
        environment_id=None,
        policy={
            "allowed_hosts": ["127.0.0.1"],
            "allowed_ports": [port],
            "allow_private_cidrs": ["127.0.0.0/8"],
        },
    )
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "api",
                "driver": "http",
                "input": {
                    "url": f"http://127.0.0.1:{port}/orders",
                    "method": "GET",
                    "assertions": assertions,
                },
            }
        ],
        "edges": [],
    }
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="QUEUED")
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    dag_scheduler.schedule(
        db, run.id, graph, dispatch=lambda row: enqueue_node_run(db, row, graph=graph)
    )
    db.commit()
    job = db.scalar(select(ExecutionJob).where(ExecutionJob.status == "pending"))
    return run, job


def test_http_200_business_error_fails_and_persists(db_session, stub_server):
    run, job = _seed(
        db_session,
        port=stub_server,
        assertions=[
            {"assertion_key": "http.status", "source": "http_status", "operator": "equals", "expected": 200},
            {"assertion_key": "biz.code", "source": "http_body", "path": "$.code", "operator": "equals", "expected": 0},
        ],
    )
    job_consumer.claim_aiqe_jobs(db_session)
    outcome = job_consumer.run_job(db_session, job.id)
    db_session.expire_all()

    assert outcome["node_status"] == "FAILED"
    assert outcome["assertion_aggregate"] == FAIL
    node = db_session.scalar(select(NodeRun).where(NodeRun.run_id == run.id))
    assert node.status == "FAILED"
    assert node.error_class == "ASSERTION_FAILED"
    run_row = db_session.get(TestRun, run.id)
    assert run_row.outcome == "FAIL"

    rows = list(
        db_session.scalars(
            select(RunAssertionResult)
            .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
            .where(StepAttempt.node_run_id == node.id)
        )
    )
    by_key = {row.assertion_key: row for row in rows}
    assert by_key["http.status"].status == PASS
    assert by_key["biz.code"].status == FAIL
    assert by_key["biz.code"].expected_json == 0
    assert by_key["biz.code"].actual_json == 4001
    assert by_key["biz.code"].evaluator_version.startswith("1.0.0")


def test_all_assertions_pass_marks_node_passed(db_session, stub_server):
    run, job = _seed(
        db_session,
        port=stub_server,
        assertions=[
            {"assertion_key": "biz.code", "source": "http_body", "path": "$.code", "operator": "equals", "expected": 4001},
        ],
        key="RUN-AUD007-2",
    )
    job_consumer.claim_aiqe_jobs(db_session)
    outcome = job_consumer.run_job(db_session, job.id)
    assert outcome["node_status"] == "PASSED"
    assert outcome["assertion_aggregate"] == PASS


def test_assertions_endpoint_lists_results(client, auth_headers, db_session, stub_server):
    run, job = _seed(
        db_session,
        port=stub_server,
        assertions=[
            {"assertion_key": "biz.code", "source": "http_body", "path": "$.code", "operator": "equals", "expected": 0},
        ],
        key="RUN-AUD007-3",
    )
    job_consumer.claim_aiqe_jobs(db_session)
    job_consumer.run_job(db_session, job.id)
    db_session.commit()

    client.headers.update(auth_headers)
    resp = client.get(f"/api/v1/aiqe/runs/{run.id}/assertions")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["assertion_key"] == "biz.code"
    assert item["status"] == FAIL
    assert item["expected"] == 0
    assert item["actual"] == 4001
    assert item["evaluator_key"] == "aiqe.assertion.engine"


def test_assertions_endpoint_enforces_project_scope(client, auth_headers, db_session):
    run = TestRun(project_id=2, run_key="RUN-OTHER-ASSERT", status="DRAFT")
    db_session.add(run)
    db_session.commit()
    client.headers.update(auth_headers)
    assert client.get(f"/api/v1/aiqe/runs/{run.id}/assertions").status_code == 404
