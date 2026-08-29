"""EvidenceSanitizer security tests (V31-006)."""
from __future__ import annotations

import json

from app.modules.aitde.common.enums import SanitizationStatus
from app.modules.aitde.evidence.sanitizer import sanitize, sanitize_headers


def test_headers_redact_authorization_and_cookie():
    out = sanitize_headers({"Authorization": "Bearer abc", "X-Env": "dev", "Cookie": "sid=1"})
    assert out["Authorization"] == "<REDACTED>"
    assert out["Cookie"] == "<REDACTED>"
    assert out["X-Env"] == "dev"


def test_json_body_redacts_secret_fields():
    body = json.dumps({"password": "secret123", "ok": True}).encode()
    safe, status = sanitize(body, "application/json")
    assert status == SanitizationStatus.SANITIZED.value
    parsed = json.loads(safe)
    assert parsed["password"] == "<REDACTED>"
    assert parsed["ok"] is True


def test_bearer_token_stripped_in_text():
    safe, status = sanitize(b"Authorization Bearer abc123.def", "text/plain")
    assert status == SanitizationStatus.SANITIZED.value
    assert b"abc123.def" not in safe


def test_unparseable_json_is_rejected():
    # sanitize() swallows SanitizeError and reports a REJECTED status
    safe, status = sanitize(b'{"broken": ', "application/json")
    assert status == SanitizationStatus.REJECTED.value
    assert safe == b'{"broken": '
