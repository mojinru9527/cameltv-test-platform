"""M2 / TA-012 + v1.4 FIX-003：HTTP Driver Adapter。

- 真实 httpx 执行；prepare 阶段完成 URL allowlist / SSRF / secret 注入前的校验；
- 记录 method、脱敏 URL、headers 摘要、body hash、request/response 时间与 correlation id；
- 解析 JSON 供 Assertion Runtime 使用（HTTP 200 本身不再等于业务 PASS）；
- 不自动 retry；retry 只由 Workflow 显式声明，且非幂等写操作不得重放；
- 证据正文统一脱敏并限长，二进制只保留 sha256/长度。
"""
from __future__ import annotations

import hashlib
import ipaddress
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.aiqe.services.evidence_redactor import redact, redact_json_text
from app.core.config import settings

SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
    }
)
MAX_BODY_BYTES = 64 * 1024
REDACTED = "***"
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE"})
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class UnsafeTargetError(ValueError):
    """URL 未通过 allowlist / SSRF 校验。"""


@dataclass
class HttpRequestSpec:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_body: Any = None
    content: bytes | None = None
    timeout_ms: int = 15000
    correlation_id: str = ""
    idempotency_key: str = ""
    allowed_hosts: list[str] | None = None
    allow_private: bool | None = None


@dataclass
class HttpResult:
    ok: bool
    status_code: int | None
    error: str | None
    duration_ms: int
    request: dict[str, Any]
    response: dict[str, Any]
    data: dict[str, Any] = field(default_factory=dict)
    error_class: str = ""


def redact_headers(headers: dict[str, str] | httpx.Headers) -> dict[str, str]:
    return {
        key: (REDACTED if key.lower() in SENSITIVE_HEADERS else value)
        for key, value in dict(headers).items()
    }


def _truncate(text: str, limit: int) -> str:
    if len(text.encode("utf-8")) <= limit:
        return text
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore") + "…[truncated]"


def _truncate_bytes(value: bytes, limit: int) -> str:
    return value[:limit].decode("utf-8", errors="ignore")


def _is_private_host(host: str) -> bool:
    normalized = host.strip().strip(".").lower()
    if normalized in {
        "localhost",
        "localhost.localdomain",
        "metadata",
        "metadata.google.internal",
        "instance-data",
    }:
        return True
    if normalized.endswith(".local") or normalized.endswith(".internal"):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _host_allowed(host: str, allowed_hosts: list[str]) -> bool:
    normalized = host.strip().strip(".").lower()
    for rule in allowed_hosts:
        candidate = str(rule).strip().lower().strip()
        if not candidate:
            continue
        if candidate.startswith("*."):
            suffix = candidate[1:]
            if normalized.endswith(suffix) and normalized != suffix.lstrip("."):
                return True
        elif normalized == candidate:
            return True
    return False


def validate_target(
    url: str,
    *,
    allowed_hosts: list[str] | None = None,
    allow_private: bool | None = None,
    enforce: bool | None = None,
) -> str:
    """校验 URL；返回规范化 URL。非法 target 抛 UnsafeTargetError。"""
    enforce_ssrf = settings.aiqe_http_enforce_ssrf if enforce is None else enforce
    if not isinstance(url, str) or not url.strip():
        raise UnsafeTargetError("URL 不能为空")
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeTargetError(f"只允许 http/https: {parsed.scheme or '(空)'}")
    if not parsed.hostname:
        raise UnsafeTargetError("URL 缺少 hostname")
    if parsed.username or parsed.password:
        raise UnsafeTargetError("URL 不允许内嵌凭据")
    if not enforce_ssrf:
        return url.strip()

    hosts = allowed_hosts
    if hosts is None:
        hosts = [
            item.strip()
            for item in str(settings.aiqe_http_allowed_hosts or "").split(",")
            if item.strip()
        ]
    allow_private_target = (
        settings.aiqe_http_allow_private if allow_private is None else allow_private
    )
    host = parsed.hostname
    if hosts and not _host_allowed(host, hosts):
        raise UnsafeTargetError(f"host 不在项目 allowlist: {host}")
    if not allow_private_target and _is_private_host(host):
        raise UnsafeTargetError(f"禁止访问本机/私网/云元数据地址: {host}")
    return url.strip()


def retry_allowed(
    method: str, *, idempotency_key: str = "", policy: str = "http_semantics"
) -> bool:
    """Workflow 显式 retry 前的幂等判定。

    - http_semantics：GET/HEAD/OPTIONS/TRACE/PUT/DELETE 可重试；
    - idempotency_key：任何方法只要声明幂等键即可重试；
    - never：永不重试。
    """
    normalized = (method or "GET").upper()
    if policy == "never":
        return False
    if idempotency_key:
        return True
    if policy == "idempotency_key":
        return False
    return normalized in IDEMPOTENT_METHODS


class HttpDriver:
    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_body_bytes: int = MAX_BODY_BYTES,
        allowed_hosts: list[str] | None = None,
        allow_private: bool | None = None,
        enforce_ssrf: bool | None = None,
    ) -> None:
        self._client = client or httpx.Client(follow_redirects=True, timeout=30, trust_env=False)
        self._max_body_bytes = max(1, int(max_body_bytes))
        self._allowed_hosts = allowed_hosts
        self._allow_private = allow_private
        self._enforce_ssrf = enforce_ssrf

    def prepare(self, spec: HttpRequestSpec) -> dict[str, Any]:
        """校验并生成请求证据（不产生网络副作用）。"""
        target = validate_target(
            spec.url,
            allowed_hosts=spec.allowed_hosts
            if spec.allowed_hosts is not None
            else self._allowed_hosts,
            allow_private=spec.allow_private
            if spec.allow_private is not None
            else self._allow_private,
            enforce=self._enforce_ssrf,
        )
        headers = dict(spec.headers or {})
        correlation_id = spec.correlation_id or str(uuid.uuid4())
        headers.setdefault("X-AIQE-Correlation-ID", correlation_id)
        if spec.idempotency_key:
            headers.setdefault("Idempotency-Key", spec.idempotency_key)
        evidence: dict[str, Any] = {
            "method": spec.method.upper(),
            "url": _redact_url(target),
            "headers": redact_headers(headers),
            "timeout_ms": spec.timeout_ms,
            "correlation_id": correlation_id,
        }
        if spec.params:
            evidence["params"] = redact(spec.params, known_secrets=[])
        if spec.json_body is not None:
            body = spec.json_body
            evidence["json_body"] = redact(body, known_secrets=[])
            serialized = str(body).encode("utf-8")
            evidence["body_sha256"] = hashlib.sha256(serialized).hexdigest()
            evidence["body_bytes"] = len(serialized)
        if spec.content is not None:
            evidence["content_sha256"] = hashlib.sha256(spec.content).hexdigest()
            evidence["content_bytes"] = len(spec.content)
        evidence["retry_allowed"] = retry_allowed(
            spec.method, idempotency_key=spec.idempotency_key
        )
        return {"url": target, "headers": headers, "evidence": evidence, "correlation_id": correlation_id}

    def execute(self, spec: HttpRequestSpec) -> HttpResult:
        try:
            prepared = self.prepare(spec)
        except UnsafeTargetError as exc:
            return HttpResult(
                ok=False,
                status_code=None,
                error="UNSAFE_TARGET",
                duration_ms=0,
                request={"method": spec.method.upper(), "url": spec.url},
                response={},
                error_class="SSRF_BLOCKED",
                data={"error": str(exc)},
            )
        request_evidence = prepared["evidence"]
        method = spec.method.upper()
        target = prepared["url"]
        headers = prepared["headers"]
        started = time.monotonic()
        try:
            response = self._client.request(
                method,
                target,
                headers=headers,
                params=spec.params,
                json=spec.json_body,
                content=spec.content,
                timeout=max(0.1, spec.timeout_ms / 1000),
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            body_text = response.text
            safe_body = redact_json_text(body_text) if _looks_like_json(body_text) else redact_text(body_text)
            safe_body = _truncate(safe_body, self._max_body_bytes)
            parsed: Any = None
            try:
                parsed = response.json()
            except ValueError:
                parsed = None
            safe_headers = redact_headers(response.headers)
            return HttpResult(
                ok=200 <= response.status_code < 300,
                status_code=response.status_code,
                error=None,
                duration_ms=duration_ms,
                request=request_evidence,
                response={
                    "status_code": response.status_code,
                    "headers": safe_headers,
                    "body": safe_body,
                    "body_sha256": hashlib.sha256(response.content).hexdigest(),
                    "body_bytes": len(response.content),
                    "elapsed_ms": duration_ms,
                    "url": _redact_url(str(response.url)),
                },
                data={
                    "status_code": response.status_code,
                    "headers": safe_headers,
                    "body_text": _truncate(body_text, self._max_body_bytes),
                    "json": redact(parsed, known_secrets=[]),
                    "url": _redact_url(str(response.url)),
                    "duration_ms": duration_ms,
                    "correlation_id": prepared["correlation_id"],
                },
            )
        except httpx.TimeoutException:
            return self._failure(spec, request_evidence, started, "TIMEOUT")
        except httpx.HTTPError as exc:
            return self._failure(spec, request_evidence, started, type(exc).__name__)
        except OSError as exc:
            return self._failure(spec, request_evidence, started, f"NETWORK:{type(exc).__name__}")

    def _failure(
        self,
        spec: HttpRequestSpec,
        request_evidence: dict[str, Any],
        started: float,
        error: str,
    ) -> HttpResult:
        return HttpResult(
            ok=False,
            status_code=None,
            error=error,
            duration_ms=int((time.monotonic() - started) * 1000),
            request=request_evidence,
            response={},
            error_class="NETWORK_ERROR",
            data={"error": error, "correlation_id": request_evidence.get("correlation_id")},
        )

    def execute_chain(
        self, specs: list[HttpRequestSpec], *, stop_on_failure: bool = True
    ) -> list[HttpResult]:
        """顺序执行多接口链；默认首个失败即停，历史结果只追加不覆盖。"""
        results: list[HttpResult] = []
        for spec in specs:
            result = self.execute(spec)
            results.append(result)
            if not result.ok and stop_on_failure:
                break
        return results


def _redact_url(url: str) -> str:
    """脱敏 URL 里的 query 值（保留 key，便于排障）；不隐藏 host/path。"""
    try:
        parts = urlsplit(url)
    except ValueError:
        return redact_text(url)
    if not parts.query:
        return url
    masked = []
    for pair in parts.query.split("&"):
        if not pair:
            continue
        key, sep, _value = pair.partition("=")
        masked.append(f"{key}=***" if sep else key)
    return parts._replace(query="&".join(masked)).geturl()


def _looks_like_json(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped) and stripped[0] in "{[" and stripped[-1:] in ("}", "]")


def redact_text(text: str) -> str:
    from app.aiqe.services.evidence_redactor import redact_text as _redact_text
    return _redact_text(text)
