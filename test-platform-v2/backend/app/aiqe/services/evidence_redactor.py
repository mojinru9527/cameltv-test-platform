"""AIQE Evidence Redactor（FIX-008）。

原则：
- 在写入 DB / Artifact 之前脱敏，而不是读取时补救；
- Header / Query / JSON / Form / Response / Console / Trace metadata 全覆盖；
- 覆盖 Authorization、Cookie、password、token、api_key、手机号、邮箱、身份证；
- 允许项目追加字段名规则；
- 对二进制证据做已知 secret 的字节扫描，命中即拒绝入库（不静默放过）。
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

MASK = "***"

SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "apikey",
        "password",
        "passwd",
        "pwd",
        "secret",
        "client_secret",
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "session",
        "sessionid",
        "session_id",
        "credential",
        "credentials",
        "private_key",
        "phone",
        "mobile",
        "email",
        "id_card",
        "idcard",
        "identity_card",
    }
)

# 值级模式；顺序有意义：先遮 Authorization，再做通用 token。
VALUE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 ***"),
    (re.compile(r"(?i)\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}"), MASK),
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd|token|access_token|refresh_token|api[_-]?key|secret)"
            r"\s*[=:]\s*([^\s,;&'\"]{3,})"
        ),
        r"\1=***",
    ),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "***"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "***"),
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "***"),
)

# 不进入脱敏正文的二进制类型（trace.zip、截图等）；只做字节扫描。
BINARY_ARTIFACT_TYPES: frozenset[str] = frozenset(
    {"trace", "video", "screenshot", "har", "report"}
)


@dataclass
class RedactionResult:
    value: Any
    redacted_fields: list[str] = field(default_factory=list)

    @property
    def redacted(self) -> bool:
        return bool(self.redacted_fields)


def _is_sensitive_field(name: str, extra: Iterable[str] = ()) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")
    return normalized in SENSITIVE_FIELDS or normalized in {
        re.sub(r"[^a-z0-9]+", "_", str(item).strip().lower()).strip("_")
        for item in extra
    }


def redact_text(value: str) -> str:
    if not isinstance(value, str) or not value:
        return value
    text = value
    for pattern, replacement in VALUE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact(
    value: Any,
    *,
    field_name: str = "",
    extra_sensitive_fields: Iterable[str] = (),
    known_secrets: Iterable[str] = (),
    _path: str = "",
    _hits: list[str] | None = None,
) -> Any:
    """递归脱敏；返回新对象，不修改入参。"""
    hits = _hits if _hits is not None else []
    if field_name and _is_sensitive_field(field_name, extra_sensitive_fields):
        hits.append(_path or field_name)
        return MASK
    if isinstance(value, dict):
        return {
            key: redact(
                item,
                field_name=str(key),
                extra_sensitive_fields=extra_sensitive_fields,
                known_secrets=known_secrets,
                _path=f"{_path}.{key}" if _path else str(key),
                _hits=hits,
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            redact(
                item,
                extra_sensitive_fields=extra_sensitive_fields,
                known_secrets=known_secrets,
                _path=f"{_path}[{index}]",
                _hits=hits,
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        text = value
        for secret in known_secrets:
            if secret and str(secret) in text:
                text = text.replace(str(secret), MASK)
                hits.append(_path or field_name or "known_secret")
        cleaned = redact_text(text)
        if cleaned != text and (_path or field_name):
            hits.append(_path or field_name)
        return cleaned
    if isinstance(value, bytes):
        # 二进制不在文本层改字节（会破坏 trace/截图）；由 scan_bytes 决定拒收。
        for secret in known_secrets:
            if secret and str(secret).encode("utf-8") in value:
                hits.append(_path or field_name or "binary_secret")
                break
        return value
    return value


def redact_result(
    value: Any,
    *,
    extra_sensitive_fields: Iterable[str] = (),
    known_secrets: Iterable[str] = (),
) -> RedactionResult:
    hits: list[str] = []
    cleaned = redact(
        value,
        extra_sensitive_fields=extra_sensitive_fields,
        known_secrets=known_secrets,
        _hits=hits,
    )
    return RedactionResult(value=cleaned, redacted_fields=sorted(set(hits)))


def redact_json_text(
    text: str,
    *,
    extra_sensitive_fields: Iterable[str] = (),
    known_secrets: Iterable[str] = (),
) -> str:
    """JSON 文本脱敏；无法解析时按纯文本处理（宁可遮错，不可漏）。"""
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return redact_text(text)
    return json.dumps(
        redact(
            parsed,
            extra_sensitive_fields=extra_sensitive_fields,
            known_secrets=known_secrets,
        ),
        ensure_ascii=False,
        default=str,
    )


def scan_bytes(
    content: bytes,
    *,
    known_secrets: Iterable[str] = (),
    extra_patterns: Iterable[str] = (),
) -> list[str]:
    """扫描二进制证据；返回命中描述（空列表表示未命中）。"""
    hits: list[str] = []
    for secret in known_secrets:
        if secret and str(secret).encode("utf-8") in content:
            hits.append("known_secret")
            break
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:  # pragma: no cover - decode errors are already ignored
        text = ""
    for pattern, _replacement in VALUE_PATTERNS:
        if pattern.search(text):
            hits.append(pattern.pattern[:40])
    for extra in extra_patterns:
        if extra and re.search(extra, text):
            hits.append(str(extra)[:40])
    return sorted(set(hits))


def redact_http_exchange(
    request: dict[str, Any],
    response: dict[str, Any],
    *,
    known_secrets: Iterable[str] = (),
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """HTTP 请求/响应统一脱敏；返回 (safe_request, safe_response, hits)。"""
    hits: list[str] = []
    safe_request = redact(
        request, field_name="request", known_secrets=known_secrets, _hits=hits
    )
    safe_response = redact(
        response, field_name="response", known_secrets=known_secrets, _hits=hits
    )
    return safe_request, safe_response, sorted(set(hits))
