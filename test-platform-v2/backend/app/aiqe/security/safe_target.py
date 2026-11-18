"""AUD-001：URL 目标校验（SafeTargetValidator）。

覆盖 v1.5 §01 AUD-001「验收测试」的全部负向要求：

- 拒绝 loopback / 私网 / link-local / 保留地址 / 云元数据（169.254.169.254）；
- 拒绝 IPv4-mapped IPv6（``::ffff:127.0.0.1``）与各种混淆写法（八进制 / 十六进制 / 整数 IP）；
- DNS 解析全部 A/AAAA，**只要有一个不允许就拒绝**（避免多地址选择绕过）；
- 每次 Redirect 都重新校验 host / IP / port / method，跨主机默认拒绝，307/308 保持
  method/body 时二次授权；
- 拒绝 URL 携带 userinfo、非 http(s) scheme、IPv6 zone id、非法 IDNA。

校验结果 ``ResolvedTarget`` 带 ``policy_version`` 与 ``resolved_ips``，供证据与安全事件使用。
"""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

from app.aiqe.security.target_policy import TargetPolicy

Address = ipaddress.IPv4Address | ipaddress.IPv6Address

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
#: 301/302/303 会把非 GET/HEAD 方法改为 GET（RFC 9110 §15.4）。
METHOD_REWRITE_STATUSES = frozenset({301, 302, 303})

_NUMERIC_HOST = re.compile(
    r"^(?:0[xX][0-9a-fA-F]+|[0-9]+)(?:\.(?:0[xX][0-9a-fA-F]+|[0-9]+)){0,3}$"
)
_CONTROL = re.compile(r"[\x00-\x20\x7f]")


class TargetDenied(PermissionError):
    """目标未通过服务端策略；``code`` 进入事件与 Run 错误分类。"""

    def __init__(self, code: str, message: str, *, details: dict | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = details or {}

    def payload(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass(frozen=True)
class ResolvedTarget:
    normalized_url: str
    hostname: str
    port: int
    scheme: str
    resolved_ips: tuple[str, ...]
    policy_version: int
    checked_at: datetime
    method: str = "GET"
    is_ip_literal: bool = False
    extra: dict = field(default_factory=dict)

    def snapshot(self) -> dict:
        return {
            "normalized_url": self.normalized_url,
            "hostname": self.hostname,
            "port": self.port,
            "scheme": self.scheme,
            "resolved_ips": list(self.resolved_ips),
            "policy_version": self.policy_version,
            "checked_at": self.checked_at.isoformat(),
            "method": self.method,
            "is_ip_literal": self.is_ip_literal,
        }


def _default_resolver(host: str, port: int) -> set[Address]:
    import socket

    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise TargetDenied("DNS_RESOLUTION_FAILED", f"无法解析目标主机: {host}") from exc
    addresses: set[Address] = set()
    for record in records:
        raw = str(record[4][0]).split("%", 1)[0]
        try:
            addresses.add(ipaddress.ip_address(raw))
        except ValueError:
            continue
    if not addresses:
        raise TargetDenied("DNS_RESOLUTION_FAILED", f"目标主机没有可用地址: {host}")
    return addresses


def _unwrap(address: Address) -> Address:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def _parse_port(parsed) -> int:
    try:
        port = parsed.port
    except ValueError as exc:
        raise TargetDenied("PORT_INVALID", "URL 端口无效") from exc
    if port is None:
        return 443 if parsed.scheme == "https" else 80
    return port


def normalize_host(raw: str) -> str:
    """规范化主机名；拒绝混淆写法与不支持的字符。"""
    host = str(raw or "").strip()
    if not host:
        raise TargetDenied("HOST_MISSING", "URL 缺少主机名")
    if "%" in host:
        raise TargetDenied("ZONE_ID_NOT_ALLOWED", "不允许 IPv6 zone id")
    if any(char in host for char in ("*", "/", "\\", "@", " ", "\t", "\n", "\r")):
        raise TargetDenied("HOST_INVALID", f"主机名含非法字符: {host}")
    try:
        # IDNA 规范化（中文域名等）；非法 IDNA 直接 fail closed。
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise TargetDenied("HOST_INVALID", f"主机名 IDNA 非法: {host}") from exc
    host = host.lower().rstrip(".")
    if not host or host == ".":
        raise TargetDenied("HOST_INVALID", "主机名为空")
    if _NUMERIC_HOST.match(host):
        try:
            ipaddress.ip_address(host)
        except ValueError as exc:
            # 2130706433 / 0177.0.0.1 / 0x7f.0.0.1 这类写法会被系统解析器当成 IP，
            # 但不在 ipaddress 的严格语法内 —— 必须拒绝，避免"字符串不同、连接同一地址"。
            raise TargetDenied(
                "AMBIGUOUS_NUMERIC_HOST", f"拒绝混淆数字主机写法: {host}"
            ) from exc
    return host


def _check_address(address: Address, policy: TargetPolicy) -> None:
    candidate = _unwrap(address)
    for network in policy.blocked_networks:
        if candidate.version == network.version and candidate in network:
            raise TargetDenied(
                "ADDRESS_BLOCKED",
                f"目标地址在禁止网段 {network}: {candidate}",
                details={"ip": str(candidate), "cidr": str(network)},
            )
    if candidate.is_global:
        return
    for network in policy.allowed_networks:
        if candidate.version == network.version and candidate in network:
            return
    raise TargetDenied(
        "PRIVATE_ADDRESS_DENIED",
        f"禁止访问私网/回环/链路本地/保留地址: {candidate}",
        details={"ip": str(candidate)},
    )


class SafeTargetValidator:
    """URL → ``ResolvedTarget``；所有失败都以 ``TargetDenied`` 表达。"""

    def __init__(self, resolver: Callable[[str, int], Iterable[Address]] | None = None) -> None:
        self._resolver = resolver or _default_resolver

    # ── 主校验 ──────────────────────────────────────────────
    def validate(self, url: str, policy: TargetPolicy, *, method: str = "GET") -> ResolvedTarget:
        raw = str(url or "").strip()
        if not raw:
            raise TargetDenied("URL_MISSING", "URL 不能为空")
        if _CONTROL.search(raw):
            raise TargetDenied("URL_INVALID", "URL 含空白或控制字符")
        if "\\" in raw:
            raise TargetDenied("URL_INVALID", "URL 不允许反斜杠")
        try:
            parsed = urlsplit(raw)
        except ValueError as exc:
            raise TargetDenied("URL_INVALID", "URL 解析失败") from exc

        scheme = (parsed.scheme or "").lower()
        if scheme not in policy.allowed_schemes:
            raise TargetDenied(
                "SCHEME_NOT_ALLOWED", f"不允许的 scheme: {scheme or '(空)'}"
            )
        if parsed.username is not None or parsed.password is not None:
            raise TargetDenied("USERINFO_NOT_ALLOWED", "URL 不允许携带用户名或密码")
        if parsed.fragment:
            # fragment 不会发送到服务端，但出现通常意味着调用方拼错；保留但不影响安全。
            pass

        host = normalize_host(parsed.hostname or "")
        port = _parse_port(parsed)
        verb = (method or "GET").strip().upper()
        if verb not in policy.allowed_methods:
            raise TargetDenied("METHOD_NOT_ALLOWED", f"不允许的 HTTP 方法: {verb}")
        if policy.allowed_ports:
            if port not in policy.allowed_ports:
                raise TargetDenied(
                    "PORT_NOT_ALLOWED",
                    f"端口 {port} 不在允许列表 {list(policy.allowed_ports)}",
                )
        elif port not in (80, 443):
            raise TargetDenied(
                "PORT_NOT_ALLOWED", f"未配置 allowed_ports 时只允许 80/443，实际 {port}"
            )

        if not policy.allows_host(host):
            raise TargetDenied(
                "HOST_NOT_ALLOWED",
                f"主机 {host} 不在项目允许列表" if not policy.is_deny_all else "项目未配置目标访问策略（默认拒绝）",
                details={"host": host, "policy_version": policy.version},
            )

        is_literal = False
        literal: Address | None = None
        try:
            literal = ipaddress.ip_address(host)
            is_literal = True
        except ValueError:
            literal = None

        resolved: tuple[str, ...]
        if literal is not None:
            _check_address(literal, policy)
            resolved = (str(literal),)
        else:
            addresses = {_unwrap(a) for a in self._resolver(host, port)}
            if not addresses:
                raise TargetDenied("DNS_RESOLUTION_FAILED", f"目标主机没有可用地址: {host}")
            # 只要有一个解析结果不允许就拒绝，避免多地址选择绕过。
            for address in sorted(addresses, key=str):
                _check_address(address, policy)
            resolved = tuple(sorted({str(a) for a in addresses}))

        normalized = f"{scheme}://{host}"
        if not is_literal and ":" in host:
            normalized = f"{scheme}://[{host}]"
        default_port = 443 if scheme == "https" else 80
        if parsed.port is not None or port != default_port:
            normalized = f"{normalized}:{port}"
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        normalized = f"{normalized}{path}{query}"

        return ResolvedTarget(
            normalized_url=normalized,
            hostname=host,
            port=port,
            scheme=scheme,
            resolved_ips=resolved,
            policy_version=policy.version,
            checked_at=datetime.now(UTC),
            method=verb,
            is_ip_literal=is_literal,
        )

    # ── Redirect 二次校验 ───────────────────────────────────
    def validate_redirect(
        self,
        previous: ResolvedTarget,
        location: str,
        status_code: int,
        method: str,
        policy: TargetPolicy,
    ) -> tuple[ResolvedTarget, str]:
        target_location = str(location or "").strip()
        if not target_location:
            raise TargetDenied("REDIRECT_LOCATION_MISSING", "重定向缺少 Location")
        absolute = urljoin(previous.normalized_url, target_location)
        next_method = (method or "GET").strip().upper()
        if int(status_code) in METHOD_REWRITE_STATUSES and next_method not in ("GET", "HEAD"):
            next_method = "GET"
        target = self.validate(absolute, policy, method=next_method)
        if target.hostname != previous.hostname:
            if not policy.allow_cross_host_redirect:
                raise TargetDenied(
                    "CROSS_HOST_REDIRECT_DENIED",
                    f"跨主机重定向默认拒绝: {previous.hostname} → {target.hostname}",
                    details={"from": previous.hostname, "to": target.hostname},
                )
            if target.port != previous.port:
                raise TargetDenied(
                    "CROSS_HOST_REDIRECT_DENIED",
                    f"跨主机重定向变更加端口: {previous.port} → {target.port}",
                )
        return target, next_method


__all__ = [
    "METHOD_REWRITE_STATUSES",
    "REDIRECT_STATUSES",
    "ResolvedTarget",
    "SafeTargetValidator",
    "TargetDenied",
    "normalize_host",
]
