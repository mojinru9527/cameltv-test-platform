"""统一出网守卫：用户可控 URL 出网前的唯一断言入口。

背景（Batch 258 / B1-1）：同一份「私网 / 回环 / 链路本地拒绝 + 重定向二次校验」策略此前只存在于
`app/core/outbound_policy.py`，而需求抓取、发布包导入两条链路各自实现了弱化版本，导致
`cameltv-bug-guard` S1 跨 98 个提交未关闭。本模块把**纯 URL 策略**抽为单一实现：

- `outbound_policy` 反向依赖本模块（不再保留第二套 IP 判定）；
- 非 GET 链路（带凭据 Header 的抓取、下载、导入）可直接复用 `assert_public_url()`。

设计约束：本模块**不导入 settings**，保持无副作用、可离线单测（解析器可注入）。
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import SplitResult, urljoin, urlsplit

Address = ipaddress.IPv4Address | ipaddress.IPv6Address

_ALLOWED_SCHEMES = {"http", "https"}
_PRIVATE_HINT = "禁止访问私网、回环、链路本地或保留地址"


class UrlNotAllowedError(ValueError):
    """用户可控 URL 未通过出网策略。"""


def resolve_addresses(host: str, port: int) -> set[Address]:
    """解析全部 A/AAAA 记录；解析失败或结果为空即拒绝（fail closed）。"""
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UrlNotAllowedError(f"无法解析目标主机: {host}") from exc
    addresses: set[Address] = set()
    for record in records:
        raw = record[4][0]
        try:
            addresses.add(ipaddress.ip_address(raw))
        except ValueError:
            continue
    if not addresses:
        raise UrlNotAllowedError(f"目标主机没有可用地址: {host}")
    return addresses


def effective_port(parsed: SplitResult) -> int:
    """返回显式端口或 scheme 默认端口。"""
    if parsed.port is not None:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def parse_http_url(url: str) -> SplitResult:
    """校验 scheme / 主机名 / 凭据 / 端口，返回解析结果。"""
    parsed = urlsplit((url or "").strip())
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UrlNotAllowedError("仅允许 http/https URL")
    if not parsed.hostname:
        raise UrlNotAllowedError("URL 缺少主机名")
    if parsed.username is not None or parsed.password is not None:
        raise UrlNotAllowedError("URL 不允许携带用户名或密码")
    try:
        port = effective_port(parsed)
    except ValueError as exc:
        raise UrlNotAllowedError("URL 端口无效") from exc
    if not 1 <= port <= 65535:
        raise UrlNotAllowedError("URL 端口无效")
    return parsed


def assert_public_url(
    url: str,
    *,
    allow_private: bool = False,
    resolver=None,
) -> str:
    """校验 URL 指向公网地址；`allow_private=True` 时跳过地址判定（内网被测系统场景）。

    `resolver` 可注入，供离线单测与「已解析地址」复用，避免二次 DNS 探测
    （同链路非幂等网络操作只做一次，见 cameltv-bug-guard）。

    Raises:
        UrlNotAllowedError: 协议/主机名/凭据/端口非法，或解析到非公网地址。
    """
    parsed = parse_http_url(url)
    if not allow_private:
        resolved = (resolver or resolve_addresses)(parsed.hostname, effective_port(parsed))
        if any(not address.is_global for address in resolved):
            raise UrlNotAllowedError(_PRIVATE_HINT)
    return parsed.geturl()


def assert_public_url_after_redirect(
    base_url: str,
    location: str,
    *,
    allow_private: bool = False,
    resolver=None,
) -> str:
    """把 `location` 解析为绝对地址后二次校验（重定向后必须重验，B1-1 DoD 第 4 类）。"""
    target = urljoin(base_url, (location or "").strip())
    return assert_public_url(target, allow_private=allow_private, resolver=resolver)
