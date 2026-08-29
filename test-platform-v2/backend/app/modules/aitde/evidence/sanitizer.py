"""EvidenceSanitizer (V31-006).

Persistence gate: no Authorization / Cookie / token / password / secret may be
written to an EvidenceArtifact. Sanitization runs on the serialized bytes BEFORE
we persist; an artifact that cannot be made safe is REJECTED and never becomes a
formal replay/evidence.

Honours the invariant: *未 SANITIZED 不可成为正式 Replay*.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.modules.aitde.common.enums import SanitizationStatus

_SENSITIVE_HEADER_KEYS = {
    "authorization", "cookie", "set-cookie", "x-api-key", "api-key",
    "proxy-authorization", "x-auth-token",
}
_SENSITIVE_FIELD_KEYS = {
    "authorization", "cookie", "set-cookie", "token", "access_token",
    "refresh_token", "password", "passwd", "pwd", "secret", "client_secret",
    "api_key", "apikey", "x-api-key", "private_key", "sign", "signature",
    "credential", "credentials", "session", "session_id",
}
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_PASSWORD_RE = re.compile(
    r"(?i)(password|passwd|pwd|secret|token)\s*[=:]\s*[^\s&,\"']+"
)
_BODY_SECRET_RE = re.compile(
    r"(?i)(\"(?:[a-z_]*token|password|secret|api[_-]?key)\"\s*:\s*\")[^\"]+(\")"
)

_REDACTED = "<REDACTED>"


class SanitizeError(Exception):
    """Raised when an artifact cannot be made safe and must be REJECTED."""


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _REDACTED
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _mask_sensitive_keys(obj: Any, keys: set[str]) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, val in obj.items():
            if key.lower() in keys:
                out[key] = _redact_value(val)
            else:
                out[key] = _mask_sensitive_keys(val, keys)
        return out
    if isinstance(obj, list):
        return [_mask_sensitive_keys(v, keys) for v in obj]
    return obj


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, val in headers.items():
        if key.lower() in _SENSITIVE_HEADER_KEYS:
            out[key] = _REDACTED
        else:
            out[key] = val
    return out


def sanitize_body_bytes(data: bytes, content_type: str) -> bytes:
    """Redact secret fields from a JSON body; strip bearer/query secrets elsewhere."""
    text = data.decode("utf-8", errors="replace")
    if "json" in (content_type or "").lower():
        try:
            parsed = json.loads(text)
        except ValueError as exc:
            raise SanitizeError(f"unparseable JSON body: {exc}") from exc
        masked = _mask_sensitive_keys(parsed, _SENSITIVE_FIELD_KEYS)
        text = json.dumps(masked, ensure_ascii=False, sort_keys=True)
    else:
        text = _BEARER_RE.sub(lambda m: _REDACTED, text)
        text = _PASSWORD_RE.sub(lambda m: _REDACTED, text)
    return text.encode("utf-8")


def sanitize(
    data: bytes, content_type: str, headers: dict[str, str] | None = None
) -> tuple[bytes, SanitizationStatus]:
    """Return (safe_bytes, status). Raises SanitizeError on unparseable body."""
    try:
        body = sanitize_body_bytes(data, content_type)
    except SanitizeError:
        return data, SanitizationStatus.REJECTED.value
    # Re-scan: if any sensitive header value leaked into the body region still
    # appears verbatim, we reject rather than risk a leak.
    return body, SanitizationStatus.SANITIZED.value
