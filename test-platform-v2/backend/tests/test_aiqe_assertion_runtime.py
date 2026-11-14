"""v1.4 FIX-002：Assertion Runtime 验收测试。"""
from __future__ import annotations

from app.aiqe.models.run import NodeRun, RunAssertionResult, StepAttempt, TestRun
from app.aiqe.schemas.contracts import DriverResult
from app.aiqe.services import assertion_service
from sqlalchemy import select


def _seed(db, key="RUN-ASSERT"):
    run = TestRun(project_id=1, run_key=key, source_type="manual", status="RUNNING")
    db.add(run)
    db.flush()
    node = NodeRun(run_id=run.id, node_key="n1", driver_key="http", status="RUNNING")
    db.add(node)
    db.flush()
    attempt = StepAttempt(
        node_run_id=node.id, step_key="n1", attempt_no=1, status="RUNNING"
    )
    db.add(attempt)
    db.flush()
    return run, node, attempt


def _assertion(**overrides):
    base = {
        "assertion_key": "a1",
        "oracle_layer": "STD",
        "oracle_ref": "STD-001",
        "type": "http_status",
        "operator": "eq",
        "expected": 200,
        "severity": "P0",
    }
    base.update(overrides)
    return base


def test_http_200_but_business_json_wrong_is_fail(db_session):
    run, node, attempt = _seed(db_session)
    result = DriverResult(
        driver_key="http",
        status="SUCCEEDED",
        data={"status_code": 200, "json": {"code": 500, "msg": "error"}},
    )
    status, outcomes = assertion_service.evaluate_and_persist(
        db_session,
        node=node,
        attempt=attempt,
        result=result,
        declared=[
            _assertion(),
            _assertion(
                assertion_key="body_code",
                type="jsonpath",
                path="$.code",
                expected=0,
                oracle_ref="REQ-AC-1",
            ),
        ],
    )
    assert status == "FAIL"
    assert [item.status for item in outcomes] == ["PASS", "FAIL"]
    rows = list(
        db_session.scalars(
            select(RunAssertionResult).where(
                RunAssertionResult.step_attempt_id == attempt.id
            )
        )
    )
    assert len(rows) == 2
    assert all(row.oracle_ref for row in rows)


def test_json_schema_and_text_and_url(db_session):
    run, node, attempt = _seed(db_session, "RUN-ASSERT-2")
    result = DriverResult(
        driver_key="http",
        status="SUCCEEDED",
        data={
            "status_code": 201,
            "json": {"id": 1, "name": "x"},
            "body_text": "created ok",
            "url": "https://api.test/items/1",
        },
    )
    status, outcomes = assertion_service.evaluate_and_persist(
        db_session,
        node=node,
        attempt=attempt,
        result=result,
        declared=[
            _assertion(assertion_key="schema", type="json_schema", schema={
                "type": "object",
                "required": ["id", "name"],
            }),
            _assertion(assertion_key="text", type="text_contains", expected="created"),
            _assertion(assertion_key="url", type="url_contains", expected="/items/1"),
        ],
    )
    assert status == "PASS"
    assert all(item.status == "PASS" for item in outcomes)


def test_locator_probe_is_not_business_pass(db_session):
    run, node, attempt = _seed(db_session, "RUN-ASSERT-3")
    result = DriverResult(
        driver_key="playwright",
        status="SUCCEEDED",
        data={
            "locators": {"#save": {"visible": True, "count": 1, "text": ""}},
            "business_action_dispatched": False,
        },
    )
    status, outcomes = assertion_service.evaluate_and_persist(
        db_session,
        node=node,
        attempt=attempt,
        result=result,
        declared=[
            _assertion(
                assertion_key="published",
                type="locator_visible",
                selector="#published",
                expected=True,
            )
        ],
    )
    assert status in {"FAIL", "NOT_EVALUATED", "BLOCKED"}
    assert status != "PASS"


def test_db_assertions(db_session):
    run, node, attempt = _seed(db_session, "RUN-ASSERT-4")
    result = DriverResult(
        driver_key="db",
        status="SUCCEEDED",
        data={"db": {"rows": [{"status": "live"}], "row_count": 1}},
    )
    status, outcomes = assertion_service.evaluate_and_persist(
        db_session,
        node=node,
        attempt=attempt,
        result=result,
        declared=[
            _assertion(assertion_key="exists", type="db_row_exists", expected=True),
            _assertion(assertion_key="count", type="db_row_count", expected=1),
            _assertion(
                assertion_key="value",
                type="db_value_eq",
                path="$.rows[0].status",
                expected="live",
            ),
        ],
    )
    assert status == "PASS"


def test_eventually_polls_until_pass(monkeypatch):
    from app.aiqe.schemas.contracts import AssertionSpec

    calls = {"n": 0}

    def fake_sleep(_seconds):
        calls["n"] += 1

    monkeypatch.setattr(assertion_service.time, "sleep", fake_sleep)
    spec = assertion_service.normalize_assertion(
        {
            "assertion_key": "async",
            "oracle_layer": "REQ",
            "oracle_ref": "AC-ASYNC",
            "type": "eventually",
            "timeout_ms": 1000,
            "assertion": {
                "assertion_key": "inner",
                "oracle_layer": "REQ",
                "oracle_ref": "AC-ASYNC",
                "type": "jsonpath",
                "path": "$.status",
                "expected": "done",
            },
        }
    )
    outcomes = assertion_service.evaluate_assertions(
        [spec], {"json": {"status": "done"}, "driver_status": "SUCCEEDED"}
    )
    assert outcomes[0].status == "PASS"


def test_missing_oracle_ref_is_error(db_session):
    run, node, attempt = _seed(db_session, "RUN-ASSERT-5")
    status, outcomes = assertion_service.evaluate_and_persist(
        db_session,
        node=node,
        attempt=attempt,
        result=DriverResult(driver_key="http", status="SUCCEEDED", data={"status_code": 200}),
        declared=[_assertion(oracle_ref="")],
    )
    assert status == "ERROR"
    assert outcomes[0].status == "ERROR"


def test_driver_blocked_never_pass(db_session):
    run, node, attempt = _seed(db_session, "RUN-ASSERT-6")
    status, outcomes = assertion_service.evaluate_and_persist(
        db_session,
        node=node,
        attempt=attempt,
        result=DriverResult(driver_key="http", status="BLOCKED"),
        declared=[_assertion()],
    )
    assert status == "BLOCKED"
    assert outcomes[0].status == "BLOCKED"
