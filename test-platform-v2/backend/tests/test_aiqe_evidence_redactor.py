"""v1.4 FIX-008：Evidence Redactor 验收测试。"""
from __future__ import annotations

from app.aiqe.services import evidence_redactor as redactor


def test_headers_query_and_json_body_redacted():
    payload = {
        "headers": {
            "Authorization": "Bearer abcdefghijklmnop",
            "Cookie": "sid=1",
            "X-Trace": "t-1",
        },
        "query": {"token": "secret-value", "page": 1},
        "body": {"password": "p@ss", "name": "alice", "phone": "13800138000"},
    }
    result = redactor.redact_result(payload)
    assert result.redacted is True
    assert result.value["headers"]["Authorization"] == "***"
    assert result.value["headers"]["Cookie"] == "***"
    assert result.value["headers"]["X-Trace"] == "t-1"
    assert result.value["query"]["token"] == "***"
    assert result.value["body"]["password"] == "***"
    assert result.value["body"]["name"] == "alice"
    assert result.value["body"]["phone"] == "***"


def test_text_patterns_cover_jwt_email_id_and_bearer():
    text = (
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "abcdefghijklmnop; user=a@b.com; card=110101199001011234; token=abc123"
    )
    cleaned = redactor.redact_text(text)
    assert "eyJhbGci" not in cleaned
    assert "a@b.com" not in cleaned
    assert "110101199001011234" not in cleaned
    assert "token=***" in cleaned


def test_known_secret_value_removed_everywhere():
    result = redactor.redact(
        {"url": "https://x.test/?k=s3cr3t", "note": "s3cr3t"},
        known_secrets=["s3cr3t"],
    )
    assert "s3cr3t" not in str(result)


def test_binary_scan_detects_secret_and_clean_binary():
    assert redactor.scan_bytes(b"\x89PNG s3cr3t", known_secrets=["s3cr3t"])
    assert redactor.scan_bytes(b"\x89PNG clean", known_secrets=["s3cr3t"]) == []


def test_redact_json_text_handles_non_json():
    assert "a@b.com" not in redactor.redact_json_text("not json a@b.com")
    assert '"password": "***"' in redactor.redact_json_text('{"password": "x"}')
