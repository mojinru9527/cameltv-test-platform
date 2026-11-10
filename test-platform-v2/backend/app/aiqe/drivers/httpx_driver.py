"""M2 / TA-012：HTTP Driver Adapter（13 号 §19 TA-012）。

- 真实 httpx 执行；返回 request/response 证据（脱敏 + 截断）；
- 多接口链：按顺序执行，默认首个失败即停（**不自动 retry**，首次失败原样保留）；
- retry 由调度层以新的 StepAttempt 表达，driver 不覆盖历史结果。
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

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


@dataclass
class HttpRequestSpec:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_body: Any = None
    content: bytes | None = None
    timeout_ms: int = 15000


@dataclass
class HttpResult:
    ok: bool
    status_code: int | None
    error: str | None
    duration_ms: int
    request: dict[str, Any]
    response: dict[str, Any]


def redact_headers(headers: dict[str, str] | httpx.Headers) -> dict[str, str]:
    return {
        key: (REDACTED if key.lower() in SENSITIVE_HEADERS else value)
        for key, value in dict(headers).items()
    }


def _truncate(text: str, limit: int) -> str:
    if len(text.encode("utf-8")) <= limit:
        return text
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore") + "…[truncated]"


class HttpDriver:
    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_body_bytes: int = MAX_BODY_BYTES,
    ) -> None:
        self._client = client or httpx.Client(follow_redirects=True, timeout=30)
        self._max_body_bytes = max(1, int(max_body_bytes))

    def _request_evidence(self, spec: HttpRequestSpec) -> dict[str, Any]:
        evidence: dict[str, Any] = {
            "method": spec.method.upper(),
            "url": spec.url,
            "headers": redact_headers(spec.headers),
            "timeout_ms": spec.timeout_ms,
        }
        if spec.params:
            evidence["params"] = spec.params
        if spec.json_body is not None:
            evidence["json_body"] = spec.json_body
        if spec.content is not None:
            evidence["content_sha256"] = hashlib.sha256(spec.content).hexdigest()
            evidence["content_bytes"] = len(spec.content)
        return evidence

    def execute(self, spec: HttpRequestSpec) -> HttpResult:
        request_evidence = self._request_evidence(spec)
        started = time.monotonic()
        try:
            response = self._client.request(
                spec.method.upper(),
                spec.url,
                headers=spec.headers,
                params=spec.params,
                json=spec.json_body,
                content=spec.content,
                timeout=max(0.1, spec.timeout_ms / 1000),
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            return HttpResult(
                ok=200 <= response.status_code < 300,
                status_code=response.status_code,
                error=None,
                duration_ms=duration_ms,
                request=request_evidence,
                response={
                    "status_code": response.status_code,
                    "headers": redact_headers(response.headers),
                    "body": _truncate(response.text, self._max_body_bytes),
                },
            )
        except httpx.TimeoutException:
            return self._failure(spec, request_evidence, started, "TIMEOUT")
        except httpx.HTTPError as exc:
            return self._failure(spec, request_evidence, started, type(exc).__name__)

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
