"""AUD-001：DNS 钉扎（pinned resolution）。

DNS Rebinding 防护的最后一环：校验时解析出的 IP 集合必须就是**实际连接**使用的 IP。
做法是在单次请求期间把 ``socket.getaddrinfo`` 对该主机的解析结果替换为已验证集合：

- 校验通过后即使 DNS 记录变化，连接仍只会落到已验证 IP；
- URL / Host 头保持不变，因此 TLS SNI 与证书校验不受影响（不需要把 IP 写进 URL）；
- 单进程内用全局锁串行化，避免并发请求互相覆盖补丁（执行器的出网请求已是低频重操作）。
"""
from __future__ import annotations

import socket
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

_PIN_LOCK = threading.RLock()


def _sockaddr(ip: str, port: int) -> tuple[int, tuple]:
    if ":" in ip:
        return (socket.AF_INET6, (ip, port, 0, 0))
    return (socket.AF_INET, (ip, port))


@contextmanager
def pinned_dns(mapping: Mapping[str, Sequence[str]]) -> Iterator[None]:
    """在 with 块内把 ``mapping`` 里的主机固定解析到给定 IP。"""
    normalized = {
        str(host).strip().lower().rstrip("."): tuple(str(ip) for ip in ips if str(ip))
        for host, ips in (mapping or {}).items()
        if host
    }
    if not normalized or not any(normalized.values()):
        yield
        return

    original = socket.getaddrinfo
    _PIN_LOCK.acquire()
    try:
        def _patched(
            host: str | bytes | None,
            port: int | str | None,
            family: int = 0,
            type: int = 0,  # 与 socket.getaddrinfo 的 type 参数同名（保持签名一致）
            proto: int = 0,
            flags: int = 0,
        ):
            key = str(host or "").strip().lower().rstrip(".")
            ips = normalized.get(key)
            if not ips:
                return original(host, port, family, type, proto, flags)
            numeric_port = 0 if port in (None, "") else int(port)
            results = []
            for ip in ips:
                fam, sockaddr = _sockaddr(ip, numeric_port)
                if family not in (0, socket.AF_UNSPEC, fam):
                    continue
                results.append((fam, type or socket.SOCK_STREAM, proto or socket.IPPROTO_TCP, "", sockaddr))
            if not results:
                raise socket.gaierror(f"没有匹配地址族的已验证 IP: {key}")
            return results

        socket.getaddrinfo = _patched  # type: ignore[assignment]
        try:
            yield
        finally:
            socket.getaddrinfo = original  # type: ignore[assignment]
    finally:
        _PIN_LOCK.release()


def resolved_ips_of(host: str, port: int) -> tuple[str, ...]:
    """解析全部 A/AAAA（测试与安全事件复用）。"""
    records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return tuple(sorted({str(record[4][0]) for record in records}))


__all__ = ["pinned_dns", "resolved_ips_of"]
