from __future__ import annotations

import json

import httpx


ASSERTIONS = [
    {"type": "status_code", "operator": "eq", "expected": 200},
    {"type": "jsonpath", "path": "$.code", "operator": "eq", "expected": 0},
    {"type": "jsonpath", "path": "$.data.count", "operator": "eq", "expected": 2},
]


def test_persisted_and_quick_entrypoints_resolve_identically(db_session, monkeypatch):
    from app.models.environment import Environment, EnvironmentVariable
    from app.models.test_case import TestCase
    from app.services.api_execution_service import execute_api_case, quick_execute

    env = Environment(
        project_id=1,
        name="Parity",
        env_type="test",
        base_url="https://api.example.test",
    )
    db_session.add(env)
    db_session.flush()
    db_session.add_all([
        EnvironmentVariable(environment_id=env.id, key="PAGE", value="3"),
        EnvironmentVariable(environment_id=env.id, key="TRACE_ID", value="trace-61"),
    ])
    case = TestCase(
        project_id=1,
        title="Parity GET",
        case_type="api",
        api_method="GET",
        api_endpoint="/items?page=${PAGE}&limit=20",
        api_headers='{"X-Trace":"${TRACE_ID}"}',
        api_assertions=json.dumps(ASSERTIONS),
    )
    db_session.add(case)
    db_session.commit()

    seen: list[tuple[str, dict]] = []

    def fake_request(_client, method, url, **kwargs):
        seen.append((str(url), kwargs.get("headers", {})))
        return httpx.Response(
            200,
            json={"code": 0, "data": {"count": 2}},
            headers={"Content-Type": "application/json"},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(httpx.Client, "request", fake_request)

    persisted = execute_api_case(
        db_session,
        case.id,
        project_id=1,
        environment_id=env.id,
    )
    quick = quick_execute(
        db_session,
        {
            "method": "GET",
            "url": "/items",
            "headers": {"X-Trace": "${TRACE_ID}"},
            "query_params": {"page": "${PAGE}", "limit": 20},
        },
        assertions=ASSERTIONS,
        project_id=1,
        environment_id=env.id,
    )

    assert [url for url, _headers in seen] == [
        "https://api.example.test/items?page=3&limit=20",
        "https://api.example.test/items?page=3&limit=20",
    ]
    assert all(headers["X-Trace"] == "trace-61" for _url, headers in seen)
    for result in (persisted, quick):
        assert result["environment_id"] == env.id
        assert result["resolved_url"] == seen[0][0]
        assert result["assertion_summary"] == {"total": 3, "passed": 3, "failed": 0}
        assert result["assertions"][2]["expected"] == 2
        assert isinstance(result["assertions"][2]["expected"], int)
        assert result["error_type"] == ""
        assert result["execution_id"].startswith("APIEXEC-")


def test_empty_assertions_fail_invalid_case_before_network(db_session, monkeypatch):
    from app.services.api_execution_service import quick_execute

    network_calls = 0

    def fail_if_called(*_args, **_kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("network must not be called")

    monkeypatch.setattr(httpx.Client, "request", fail_if_called)

    result = quick_execute(
        db_session,
        {"method": "GET", "url": "https://example.test/health"},
        assertions=[],
    )

    assert result["status"] == "error"
    assert result["error_type"] == "INVALID_CASE"
    assert result["all_pass"] is False
    assert network_calls == 0


def test_approved_release_case_requires_status_business_code_and_core_field(
    db_session, monkeypatch,
):
    from app.models.test_case import TestCase
    from app.services.api_execution_service import execute_api_case

    case = TestCase(
        project_id=1,
        title="Approved release case",
        case_type="api",
        review_status="approved",
        api_method="GET",
        api_endpoint="https://example.test/release",
        api_assertions=json.dumps([
            {"type": "status_code", "operator": "eq", "expected": 200},
        ]),
    )
    db_session.add(case)
    db_session.commit()
    network_calls = 0

    def fail_if_called(*_args, **_kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("network must not be called")

    monkeypatch.setattr(httpx.Client, "request", fail_if_called)
    result = execute_api_case(db_session, case.id, project_id=1)

    assert result["error_type"] == "INVALID_CASE"
    assert "business-code" in result["error"]
    assert "core-field" in result["error"]
    assert network_calls == 0
