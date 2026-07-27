"""按 RunContext 构造 httpx 客户端：自动注入每环境的代理与鉴权。

访问 camel1.to 等站点需经上游代理；代理取自 env.proxy，回退到 platform.default_proxy。
"""
from __future__ import annotations

from typing import Any

import httpx

from core.models import ApiDef, RunContext


def build_client(ctx: RunContext, timeout: float = 30.0) -> httpx.Client:
    headers = {"User-Agent": "camel-test-platform/0.1"}
    if ctx.env_cfg.auth_token:
        headers["Authorization"] = f"Bearer {ctx.env_cfg.auth_token}"
    proxy = ctx.proxy or None
    return httpx.Client(
        base_url=ctx.base_url,
        headers=headers,
        proxy=proxy,                 # httpx>=0.27 用单数 proxy
        timeout=timeout,
        verify=ctx.verify_tls,       # prod 校验证书、test 默认放行自签；env_cfg.verify_tls 可覆盖
        follow_redirects=True,
    )


def send_api(
    client: httpx.Client,
    api: ApiDef,
    overrides: dict[str, Any] | None = None,
) -> httpx.Response:
    """按 ApiDef 发起请求。overrides 可覆盖 query/body（用于回放真实流量）。"""
    overrides = overrides or {}
    query = {**api.query, **overrides.get("query", {})}
    body = {**api.body, **overrides.get("body", {})}
    headers = {**api.headers, **overrides.get("headers", {})}
    kwargs: dict[str, Any] = {"params": query, "headers": headers}
    if api.method in ("POST", "PUT", "PATCH"):
        kwargs["json"] = body
    return client.request(api.method, api.path, **kwargs)
