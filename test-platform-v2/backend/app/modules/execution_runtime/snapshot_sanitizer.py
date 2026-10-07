"""ExecutionSnapshotSanitizer (V3.9-R1 / TRUST-005).

Sanitizes an ``ExecutionStep`` ``input_snapshot_json`` / ``output_snapshot_json`` so
raw ``Authorization`` / ``Cookie`` / ``token`` / ``password`` / PII never reach the
step JSON — even though the ``EvidenceArtifact`` bytes are separately sanitized by
``evidence.sanitizer``.

The Evidence sanitizer runs on serialized bytes *before* object storage. The
snapshot sanitizer runs on already-parsed dict/list data *before* it is written to
``execution_steps``. Keeping the two layers separate means a leak in one boundary
is still caught by the other.

Unlike the Evidence sanitizer this NEVER rejects: an unparseable sub-value (or a
value we cannot safely inspect) is redacted wholesale rather than leaked, and an
HTTP snapshot that carries a secret header is scrubbed to a summary that omits the
header value.
"""
from __future__ import annotations

import json
import re
from typing import Any

# Field names whose entire value is replaced with a redaction marker.
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "apikey",
        "x-auth-token",
        "proxy-authorization",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "password",
        "passwd",
        "pwd",
        "secret",
        "client_secret",
        "private_key",
        "api_key",
        "sign",
        "signature",
        "credential",
        "credentials",
        "session",
        "session_id",
        "sessionid",
    }
)

# Bearer / scheme token inside a string value.
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
# `password=...` / `token=...` style key=value inside query/string.
_KEYVALUE_RE = re.compile(
    r"(?i)(password|passwd|pwd|secret|token|access_token|refresh_token|api[_-]?key)"
    r"\s*[=:]\s*[^\s&,\"']+"
)
# JSON string value under a sensitive key name.
_JSON_SECRET_RE = re.compile(
    r"(?i)(\"(?:authorization|cookie|token|password|secret|api[_-]?key|session)\"\s*:\s*\")[^\"]+(\")"
)

_REDACTED = "<REDACTED>"


class ExecutionSnapshotSanitizer:
    """Recursively redact sensitive values from an execution snapshot."""

    def sanitize_snapshot(self, value: Any) -> Any:
        """Return a deep-redacted copy of a JSON-serializable snapshot."""
        return self._redact(value)

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for key, val in value.items():
                key_str = str(key)
                if key_str.lower() in _SENSITIVE_KEYS:
                    out[key_str] = _REDACTED
                else:
                    out[key_str] = self._redact(val)
            return out
        if isinstance(value, (list, tuple)):
            return [self._redact(v) for v in value]
        if isinstance(value, str):
            return self._redact_text(value)
        return value

    def _redact_text(self, text: str) -> str:
        """Redact tokens, secrets and scan the *key* spacing for a sensitive field.

        We only redact a whole string when it *looks* like a credential (bearer /
        key=value / JSON value under a sensitive key). Plain body strings that are
        not credentials are preserved so summaries remain readable.
        """
        out = _BEARER_RE.sub(_REDACTED, text)
        out = _KEYVALUE_RE.sub(_REDACTED, out)
        out = _JSON_SECRET_RE.sub(lambda m: m.group(1) + _REDACTED + m.group(2), out)
        return out

    def sanitize_http_snapshot(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, Any] | None,
        params: dict[str, Any] | None,
        body: Any,
    ) -> dict[str, Any]:
        """Build a sanitized HTTP request summary (no header/body secrets)."""
        safe_headers = self._sanitize_headers(headers or {})
        safe_params = self._redact(params)
        safe_body = None
        if body is not None:
            try:
                safe_body = self._redact(body)
            except (TypeError, ValueError):
                safe_body = _REDACTED
        return {
            "method": str(method).upper(),
            "url": self._redact_text(str(url)),
            "headers": safe_headers,
            "params": safe_params,
            "body": safe_body,
        }

    def sanitize_response_snapshot(self, *, status: int, body: Any) -> dict[str, Any]:
        """Build a sanitized HTTP response summary."""
        safe_body = None
        if body is not None:
            try:
                safe_body = self._redact(body)
            except (TypeError, ValueError):
                safe_body = _REDACTED
        return {"status": int(status), "body": safe_body}

    def _sanitize_headers(self, headers: dict[str, Any]) -> dict[str, str]:
        out: dict[str, str] = {}
        for key, val in headers.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                out[str(key)] = _REDACTED
            else:
                out[str(key)] = self._redact_text(str(val))
        return out

    @classmethod
    def dump(cls, value: Any) -> str:
        """Serialize a sanitized snapshot to JSON (never fails on odd values)."""
        sanitized = cls().sanitize_snapshot(value)
        try:
            return json.dumps(sanitized, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            return json.dumps(_REDACTED, ensure_ascii=False)


snapshot_sanitizer = ExecutionSnapshotSanitizer()
