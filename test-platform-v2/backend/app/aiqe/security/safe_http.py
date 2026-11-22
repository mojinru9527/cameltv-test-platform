"""AUD-001：SafeHttpExecutor —— 唯一允许出网的 HTTP 执行入口。

行为契约（v1.5 §01 AUD-001「实现任务」6-9）：

- 目标校验**先于**任何网络动作；未通过策略时返回 ``blocked`` 结果，不发出请求；
- 关闭 httpx 自动跳转，手动逐跳校验 Location 的 host / IP / port / method；
- 连接期间用 ``pinned_dns`` 把目标主机固定到已验证 IP（DNS Rebinding 防护）；
- 请求 / 响应体按策略限额截断，证据统一脱敏，并携带 ``policy_version`` 与
  ``target_resolution_snapshot``；
- 安全拒绝归类为 BLOCKED / POLICY_DENIED，**不得**被当作产品接口 FAIL。
"""
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.aiqe.security.dns_pin import pinned_dns
from app.aiqe.security.safe_target import (
    REDIRECT_STATUSES,
    ResolvedTarget,
    SafeTargetValidator,
    TargetDenied,
)
from app.aiqe.security.target_policy import TargetPolicy

SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "x-auth-token",
    }
)
REDACTED = "***"
#: 工作流不得通过节点输入覆盖这些策略项（出现即忽略并记录）。
POLICY_OVERRIDE_KEYS = frozenset(
    {
        "allow_private",
        "allow_private_cidrs",
        "allowed_hosts",
        "allowed_ports",
        "allowed_schemes",
        "allowed_methods",
        "blocked_cidrs",
        "max_redirects",
        "follow_redirects",
        "verify_tls",
        "proxy",
        "proxy_url",
        "trust_env",
        "target_policy",
        "policy",
    }
)


def redact_headers(headers: Mapping[str, str] | httpx.Headers) -> dict[str, str]:
    return {
        str(key): (REDACTED if str(key).lower() in SENSITIVE_HEADERS else str(value))
        for key, value in dict(headers).items()
    }


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8", errors="ignore")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore"), True


@dataclass(frozen=True)
class SafeRequest:
    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    params: Mapping[str, Any] | None = None
    json_body: Any = None
    content: bytes | None = None
    timeout_ms: int | None = None


@dataclass(frozen=True)
class SafeHttpResult:
    ok: bool
    status_code: int | None
    duration_ms: int
    request: dict[str, Any]
    response: dict[str, Any]
    resolution: dict[str, Any] | None = None
    redirect_chain: tuple[dict[str, Any], ...] = ()
    error: str | None = None
    error_code: str = ""
    blocked: bool = False
    policy_version: int = 0

    @property
    def policy_denied(self) -> bool:
        return self.blocked


class SafeHttpExecutor:
    """策略强制的 HTTP 执行器；``client_factory`` 仅用于测试注入 MockTransport。"""

    def __init__(
        self,
        *,
        validator: SafeTargetValidator | None = None,
        client_factory: Callable[[TargetPolicy], httpx.Client] | None = None,
    ) -> None:
        self._validator = validator or SafeTargetValidator()
        self._client_factory = client_factory or self._default_client

    @staticmethod
    def _default_client(policy: TargetPolicy) -> httpx.Client:
        return httpx.Client(
            follow_redirects=False,
            verify=policy.verify_tls,
            timeout=httpx.Timeout(
                connect=policy.connect_timeout_ms / 1000,
                read=policy.read_timeout_ms / 1000,
                write=policy.read_timeout_ms / 1000,
                pool=policy.connect_timeout_ms / 1000,
            ),
        )

    # ── 公共入口 ────────────────────────────────────────────
    def request(self, request: SafeRequest, policy: TargetPolicy) -> SafeHttpResult:
        started = time.monotonic()
        # V16-001：只有显式 ALLOW 决策才允许任何网络动作；其余决策一律拒绝，
        # 且必须在创建 httpx.Client 之前返回。
        decision = getattr(policy, "decision", None)
        decision_value = str(getattr(decision, "value", decision or ""))
        if decision_value != "ALLOW":
            code = str(
                getattr(policy, "reason_code", "")
                or f"TARGET_POLICY_{decision_value or 'UNAVAILABLE'}"
            )
            return self._denied(
                request,
                policy,
                TargetDenied(code, f"目标策略未授权（decision={decision_value or 'UNKNOWN'}）"),
                started,
            )
        method = (request.method or "GET").strip().upper()
        try:
            target = self._validator.validate(request.url, policy, method=method)
        except TargetDenied as exc:
            return self._denied(request, policy, exc, started)

        body_bytes = request.content
        if body_bytes is not None and len(body_bytes) > policy.max_request_bytes:
            return self._denied(
                request,
                policy,
                TargetDenied(
                    "REQUEST_TOO_LARGE",
                    f"请求体 {len(body_bytes)} 字节超过上限 {policy.max_request_bytes}",
                ),
                started,
            )

        request_evidence: dict[str, Any] = {
            "method": method,
            "url": target.normalized_url,
            "headers": redact_headers(request.headers),
            "timeout_ms": request.timeout_ms,
            "policy_version": policy.version,
            "target_resolution_snapshot": target.snapshot(),
        }
        if request.params:
            request_evidence["params"] = dict(request.params)
        if request.json_body is not None:
            request_evidence["json_body"] = request.json_body
        if body_bytes is not None:
            request_evidence["content_sha256"] = hashlib.sha256(body_bytes).hexdigest()
            request_evidence["content_bytes"] = len(body_bytes)

        redirect_chain: list[dict[str, Any]] = []
        current_target = target
        current_method = method
        current_json = request.json_body
        current_content = body_bytes
        current_params = request.params
        hops = 0

        timeout: Any
        if request.timeout_ms:
            timeout = max(0.1, request.timeout_ms / 1000)
        else:
            timeout = httpx.Timeout(
                connect=policy.connect_timeout_ms / 1000,
                read=policy.read_timeout_ms / 1000,
                write=policy.read_timeout_ms / 1000,
                pool=policy.connect_timeout_ms / 1000,
            )

        try:
            client = self._client_factory(policy)
        except Exception as exc:  # 客户端构造失败属于执行环境问题
            return SafeHttpResult(
                ok=False,
                status_code=None,
                duration_ms=int((time.monotonic() - started) * 1000),
                request=request_evidence,
                response={},
                resolution=target.snapshot(),
                error=f"CLIENT_INIT_FAILED: {type(exc).__name__}: {exc}",
                error_code="CLIENT_INIT_FAILED",
                policy_version=policy.version,
            )

        try:
            with client:
                while True:
                    with pinned_dns({current_target.hostname: current_target.resolved_ips}):
                        response = client.request(
                            current_method,
                            current_target.normalized_url,
                            headers=dict(request.headers or {}),
                            params=dict(current_params) if current_params else None,
                            json=current_json,
                            content=current_content,
                            timeout=timeout,
                        )
                    status = int(response.status_code)
                    location = response.headers.get("location")

                    if status in REDIRECT_STATUSES and location:
                        if hops >= policy.max_redirects:
                            return SafeHttpResult(
                                ok=False,
                                status_code=status,
                                duration_ms=int((time.monotonic() - started) * 1000),
                                request=request_evidence,
                                response={},
                                resolution=target.snapshot(),
                                redirect_chain=tuple(redirect_chain),
                                error="重定向次数超过策略上限",
                                error_code="REDIRECT_LIMIT_EXCEEDED",
                                blocked=True,
                                policy_version=policy.version,
                            )
                        try:
                            next_target, next_method = self._validator.validate_redirect(
                                current_target, location, status, current_method, policy
                            )
                        except TargetDenied as exc:
                            redirect_chain.append(
                                {
                                    "status": status,
                                    "from": current_target.normalized_url,
                                    "location": location,
                                    "denied": exc.payload(),
                                }
                            )
                            return SafeHttpResult(
                                ok=False,
                                status_code=status,
                                duration_ms=int((time.monotonic() - started) * 1000),
                                request=request_evidence,
                                response={
                                    "status_code": status,
                                    "headers": redact_headers(response.headers),
                                },
                                resolution=target.snapshot(),
                                redirect_chain=tuple(redirect_chain),
                                error=exc.message,
                                error_code=exc.code,
                                blocked=True,
                                policy_version=policy.version,
                            )
                        redirect_chain.append(
                            {
                                "status": status,
                                "from": current_target.normalized_url,
                                "to": next_target.normalized_url,
                                "method": next_method,
                            }
                        )
                        hops += 1
                        current_target = next_target
                        current_method = next_method
                        current_params = None
                        if next_method in ("GET", "HEAD"):
                            current_json = None
                            current_content = None
                        continue

                    body_text, truncated = _truncate(response.text, policy.max_response_bytes)
                    response_evidence = {
                        "status_code": status,
                        "headers": redact_headers(response.headers),
                        "body": body_text,
                        "body_truncated": truncated,
                        "policy_version": policy.version,
                    }
                    return SafeHttpResult(
                        ok=200 <= status < 300,
                        status_code=status,
                        duration_ms=int((time.monotonic() - started) * 1000),
                        request=request_evidence,
                        response=response_evidence,
                        resolution=target.snapshot(),
                        redirect_chain=tuple(redirect_chain),
                        policy_version=policy.version,
                    )
        except httpx.TimeoutException:
            return self._failure(request_evidence, target, started, "TIMEOUT", policy)
        except httpx.HTTPError as exc:
            return self._failure(
                request_evidence, target, started, type(exc).__name__, policy, detail=str(exc)
            )
        except Exception as exc:  # 兜底：执行器异常不能悬挂节点
            return self._failure(
                request_evidence,
                target,
                started,
                "DRIVER_ERROR",
                policy,
                detail=f"{type(exc).__name__}: {exc}",
            )

    # ── 内部 ────────────────────────────────────────────────
    def _denied(
        self,
        request: SafeRequest,
        policy: TargetPolicy,
        exc: TargetDenied,
        started: float,
    ) -> SafeHttpResult:
        return SafeHttpResult(
            ok=False,
            status_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            request={
                "method": (request.method or "GET").strip().upper(),
                "url": str(request.url or ""),
                "headers": redact_headers(request.headers),
                "policy_version": policy.version,
                "policy_snapshot": policy.snapshot(),
                "denial": exc.payload(),
            },
            response={},
            error=exc.message,
            error_code=exc.code,
            blocked=True,
            policy_version=policy.version,
        )

    def _failure(
        self,
        request_evidence: dict[str, Any],
        target: ResolvedTarget,
        started: float,
        code: str,
        policy: TargetPolicy,
        *,
        detail: str = "",
    ) -> SafeHttpResult:
        return SafeHttpResult(
            ok=False,
            status_code=None,
            duration_ms=int((time.monotonic() - started) * 1000),
            request=request_evidence,
            response={"detail": detail} if detail else {},
            resolution=target.snapshot(),
            error=code,
            error_code=code,
            policy_version=policy.version,
        )


__all__ = [
    "POLICY_OVERRIDE_KEYS",
    "SENSITIVE_HEADERS",
    "SafeHttpExecutor",
    "SafeHttpResult",
    "SafeRequest",
    "redact_headers",
]
