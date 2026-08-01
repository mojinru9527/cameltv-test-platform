from __future__ import annotations

import json

import httpx


def test_request_snapshot_recursively_redacts_headers_query_and_json_body():
    from app.services.api_execution_service import SENSITIVE_MASK, _build_request_snapshot

    snapshot = _build_request_snapshot(
        method="POST",
        original_url="/users",
        resolved_url="https://example.test/users?token=live-token",
        headers={"Authorization": "Bearer live", "X-Trace": "safe"},
        query_params={"token": "live-token", "page": 2},
        body=json.dumps({
            "profile": {"password": "secret", "name": "safe"},
            "items": [{"api_key": "key-1", "id": 7}],
        }),
    )

    assert snapshot["headers"]["Authorization"] == SENSITIVE_MASK
    assert snapshot["query_params"] == {"token": SENSITIVE_MASK, "page": 2}
    safe_body = json.loads(snapshot["body"])
    assert safe_body["profile"] == {"password": SENSITIVE_MASK, "name": "safe"}
    assert safe_body["items"] == [{"api_key": SENSITIVE_MASK, "id": 7}]
    assert "live-token" not in snapshot["curl"]
    assert "secret" not in snapshot["curl"]


def test_response_snapshot_redacts_recursive_json_and_does_not_store_binary(db_session, monkeypatch):
    from app.services.api_execution_service import SENSITIVE_MASK, quick_execute

    responses = [
        httpx.Response(
            200,
            json={"data": {"access_token": "live", "name": "safe"}},
            headers={"Content-Type": "application/json", "Set-Cookie": "sid=secret"},
            request=httpx.Request("GET", "https://example.test/json"),
        ),
        httpx.Response(
            200,
            content=b"\x00\x01secret-binary",
            headers={"Content-Type": "application/octet-stream"},
            request=httpx.Request("GET", "https://example.test/binary"),
        ),
    ]

    monkeypatch.setattr(httpx.Client, "request", lambda *_args, **_kwargs: responses.pop(0))
    assertions = [{"type": "status_code", "operator": "eq", "expected": 200}]

    structured = quick_execute(
        db_session,
        {"method": "GET", "url": "https://example.test/json?token=live-query"},
        assertions=assertions,
    )
    binary = quick_execute(
        db_session,
        {"method": "GET", "url": "https://example.test/binary"},
        assertions=assertions,
    )

    structured_snapshot = structured["response_snapshot"]
    assert structured_snapshot["headers"]["set-cookie"] == SENSITIVE_MASK
    assert json.loads(structured_snapshot["body_preview"])["data"] == {
        "access_token": SENSITIVE_MASK,
        "name": "safe",
    }
    assert structured["resolved_url"] == "https://example.test/json?token=%2A%2A%2A"
    assert "live-query" not in json.dumps(structured)
    assert binary["response_snapshot"]["body_preview"] == "[REDACTED_UNSUPPORTED_BODY]"
    assert "secret-binary" not in json.dumps(binary["response_snapshot"])


def test_dataset_evidence_is_recursively_redacted():
    from app.services.api_execution_service import SENSITIVE_MASK, _redact_evidence

    row = {"username": "tester", "credentials": {"password": "p@ss"}, "token": "live"}

    assert _redact_evidence(row) == {
        "username": "tester",
        "credentials": {"password": SENSITIVE_MASK},
        "token": SENSITIVE_MASK,
    }
