"""V16-002 第三层：浏览器网络出口策略代理（Runner 内 egress deny-by-default）。

背景
----
Playwright 的 `context.route` 只覆盖浏览器发起的初始请求；**HTTP 重定向的目标
不会再次进入 route handler**（实测 Playwright 1.61：302 目标直接由网络栈发起）。
仅靠浏览器层无法满足规格 "每个 redirect 的新 URL 重新校验" 与
"容器/网络命名空间 egress deny-by-default"。

本模块在 Runner 进程内启动一个只绑定 `127.0.0.1` 的 HTTP 代理，Chromium 以
`--proxy-server` + `--proxy-bypass-list=<-loopback>` 强制所有请求（含 loopback、
重定向、iframe、XHR、WebSocket、弹窗）经过它：

- `CONNECT host:port`（HTTPS/WSS）：先用服务端 TargetPolicy 校验 host/port，
  再做 DNS 解析并对**全部 A/AAAA** 做地址检查；连接时直接连到已校验的 IP
  （DNS pinning，消除 rebinding 窗口），TLS 仍由浏览器端到端协商（不 MITM）。
- 绝对 URI 请求（HTTP/WS）：同样校验后连接到校验过的 IP，Host 头保持原值。
- 拒绝时返回 403/断开，并回调 `on_denial` 供 RunEvent/证据使用；
  不记录 Authorization/Cookie/query 值。

安全边界
--------
- 只监听 loopback，随机端口，仅服务本进程拉起的浏览器；
- 校验器异常 / DNS 失败 / 连接失败一律拒绝（fail closed）；
- 不代理 `CONNECT` 到非 http(s) 语义端口之外的目标（由策略端口列表决定）；
- 生产部署仍要求容器级 egress 策略作为第四道防线（见 ADR / Runbook）。
"""
from __future__ import annotations

import select
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from app.aiqe.security.safe_target import SafeTargetValidator, TargetDenied, normalize_host
from app.aiqe.security.target_policy import TargetPolicy

#: 单次响应最大缓冲（超出截断，避免 Runner 内存被大文件打爆）。
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 15
IO_TIMEOUT_SECONDS = 30
#: 不允许通过代理隧道的端口（无论策略如何配置）。
NEVER_TUNNEL_PORTS = frozenset({25, 465, 587})

HOP_BY_HOP_HEADERS = frozenset(
    {
        "proxy-connection",
        "proxy-authorization",
        "connection",
        "keep-alive",
        "transfer-encoding",
        "te",
        "trailer",
        "upgrade",
        "content-length",
    }
)


@dataclass(frozen=True)
class ProxyDenial:
    code: str
    message: str
    method: str
    host: str
    port: int
    path: str
    kind: str = "egress"


class BrowserEgressProxy:
    """策略强制的本机 HTTP(S) 代理；`denials` 记录所有拒绝（线程安全）。"""

    def __init__(
        self,
        *,
        policy: TargetPolicy,
        validator: SafeTargetValidator | None = None,
        on_denial: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.policy = policy
        self._validator = validator or SafeTargetValidator()
        self._on_denial = on_denial
        self._denials: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ── lifecycle ────────────────────────────────────────────
    def start(self) -> str:
        if self._server is not None:
            return self.proxy_url
        handler = _make_handler(self)
        handler.daemon_threads = True
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        server.daemon_threads = True
        thread = threading.Thread(
            target=server.serve_forever, name="aiqe-browser-egress-proxy", daemon=True
        )
        thread.start()
        self._server = server
        self._thread = thread
        return self.proxy_url

    def stop(self) -> None:
        server, thread = self._server, self._thread
        self._server = self._thread = None
        if server is not None:
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
        if thread is not None:
            thread.join(timeout=5)

    @property
    def proxy_url(self) -> str:
        if self._server is None:
            return ""
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def denials(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._denials)

    # ── policy ───────────────────────────────────────────────
    def deny(
        self, *, code: str, message: str, method: str, url: str, navigation: bool = False
    ) -> None:
        host = ""
        path = ""
        port = 0
        try:
            parts = urlsplit(str(url or ""))
            host = (parts.hostname or "").strip().lower()
            path = parts.path or "/"
            port = parts.port or (443 if parts.scheme == "https" else 80)
        except ValueError:
            pass
        entry = {
            "kind": "egress",
            "code": code,
            "message": str(message)[:300],
            "method": method,
            "host": host,
            "port": port,
            "path": path,
            "resource_type": "egress",
            "navigation": bool(navigation),
            "policy_version": self.policy.version,
            "policy_hash": self.policy.policy_hash,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with self._lock:
            if len(self._denials) < 200:
                self._denials.append(entry)
        if self._on_denial is not None:
            try:
                self._on_denial(entry)
            except Exception:
                pass

    def validate_target(
        self, *, authority: str, default_port: int, method: str, kind: str
    ) -> tuple[str, int, str]:
        """校验 CONNECT 目标并返回 (host, port, 校验通过的 IP)。"""
        text = str(authority or "").strip()
        if not text:
            raise TargetDenied("HOST_MISSING", "代理目标缺少 host")
        host = text
        port = default_port
        if text.startswith("["):
            closing = text.find("]")
            if closing < 0:
                raise TargetDenied("HOST_INVALID", "IPv6 目标格式非法")
            host = text[1:closing]
            rest = text[closing + 1 :]
            if rest.startswith(":"):
                port = int(rest[1:] or default_port)
        elif text.count(":") == 1:
            host, port_text = text.split(":", 1)
            if port_text:
                port = int(port_text)
        if port in NEVER_TUNNEL_PORTS:
            raise TargetDenied("PORT_NOT_ALLOWED", f"禁止隧道端口: {port}")
        normalized = normalize_host(host)
        scheme = "https" if kind in {"https", "wss"} else "http"
        url = f"{scheme}://{normalized}:{port}/"
        target = self._validator.validate(url, self.policy, method=method)
        first_ip = target.resolved_ips[0] if target.resolved_ips else ""
        return target.hostname, target.port, first_ip


def _relay(sock_a: socket.socket, sock_b: socket.socket) -> None:
    sockets = [sock_a, sock_b]
    try:
        while True:
            readable, _, _ = select.select(sockets, [], [], IO_TIMEOUT_SECONDS)
            if not readable:
                return
            for source in readable:
                data = source.recv(65536)
                if not data:
                    return
                (sock_b if source is sock_a else sock_a).sendall(data)
    except (OSError, ValueError):
        return


def _make_handler(proxy: BrowserEgressProxy) -> type:
    class _Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "AIQEEgressProxy/1.0"

        # ── 入口 ─────────────────────────────────────────
        def do_CONNECT(self):  # noqa: N802
            authority = self.path
            method = "CONNECT"
            try:
                host, port, ip = proxy.validate_target(
                    authority=authority, default_port=443, method=method, kind="https"
                )
            except TargetDenied as exc:
                proxy.deny(
                    code=exc.code,
                    message=exc.message,
                    method=method,
                    url=f"https://{authority}/",
                )
                self.send_error(403, exc.code)
                return
            except Exception as exc:  # fail closed
                proxy.deny(
                    code="TARGET_VALIDATION_ERROR",
                    message=f"{type(exc).__name__}: {exc}",
                    method=method,
                    url=f"https://{authority}/",
                )
                self.send_error(403, "TARGET_VALIDATION_ERROR")
                return
            try:
                upstream = socket.create_connection((ip, port), timeout=CONNECT_TIMEOUT_SECONDS)
            except OSError as exc:
                self.send_error(502, f"CONNECT_FAILED: {type(exc).__name__}")
                return
            try:
                self.send_response(200, "Connection Established")
                self.send_header("Proxy-Agent", "AIQEEgressProxy")
                self.end_headers()
                client = self.connection
                client.setblocking(True)
                _relay(client, upstream)
            finally:
                try:
                    upstream.close()
                except OSError:
                    pass
            self.close_connection = True

        def _handle_absolute(self) -> None:
            method = self.command
            raw_url = self.path
            upgraded = str(self.headers.get("Upgrade") or "").lower()
            try:
                parts = urlsplit(raw_url)
            except ValueError:
                self.send_error(400, "URL_INVALID")
                return
            if parts.scheme not in {"http", "https"} or not parts.hostname:
                proxy.deny(
                    code="SCHEME_NOT_ALLOWED",
                    message=f"代理只接受 http(s) 绝对 URI: {parts.scheme or '(空)'}",
                    method=method,
                    url=raw_url,
                )
                self.send_error(403, "SCHEME_NOT_ALLOWED")
                return
            port = parts.port or (443 if parts.scheme == "https" else 80)
            try:
                target = proxy._validator.validate(raw_url, proxy.policy, method=method)
            except TargetDenied as exc:
                proxy.deny(code=exc.code, message=exc.message, method=method, url=raw_url)
                self.send_error(403, exc.code)
                return
            except Exception as exc:  # fail closed
                proxy.deny(
                    code="TARGET_VALIDATION_ERROR",
                    message=f"{type(exc).__name__}: {exc}",
                    method=method,
                    url=raw_url,
                )
                self.send_error(403, "TARGET_VALIDATION_ERROR")
                return
            ip = target.resolved_ips[0] if target.resolved_ips else ""
            if upgraded == "websocket":
                self._tunnel_websocket(target, ip)
                return
            if parts.scheme == "https":
                # https 绝对 URI 不应出现（浏览器用 CONNECT）；出现即拒绝。
                proxy.deny(
                    code="PROXY_HTTPS_ABSOLUTE_DENIED",
                    message="https 请求必须使用 CONNECT",
                    method=method,
                    url=raw_url,
                )
                self.send_error(403, "PROXY_HTTPS_ABSOLUTE_DENIED")
                return
            body = b""
            length = int(self.headers.get("content-length") or 0)
            if length:
                body = self.rfile.read(min(length, MAX_RESPONSE_BYTES))
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower() not in HOP_BY_HOP_HEADERS
            }
            headers.setdefault("Host", f"{target.hostname}:{port}")
            try:
                import http.client

                connection = http.client.HTTPConnection(ip, port, timeout=IO_TIMEOUT_SECONDS)
                path = parts.path or "/"
                if parts.query:
                    path = f"{path}?{parts.query}"
                connection.request(method, path, body=body or None, headers=headers)
                response = connection.getresponse()
                # V16-002：重定向目标必须在出口层重新校验，校验失败时把响应替换为
                # 403（而不是把 30x 交给浏览器），否则 redirect 目标会绕过浏览器 route。
                if response.status in {301, 302, 303, 307, 308}:
                    location = ""
                    for key, value in response.getheaders():
                        if key.lower() == "location":
                            location = value
                            break
                    if location:
                        from urllib.parse import urljoin

                        redirected = urljoin(raw_url, location)
                        try:
                            proxy._validator.validate(
                                redirected, proxy.policy, method="GET"
                            )
                        except TargetDenied as exc:
                            proxy.deny(
                                code=exc.code,
                                message=exc.message,
                                method=method,
                                url=redirected,
                                navigation=True,
                            )
                            self.send_error(403, exc.code)
                            self.close_connection = True
                            connection.close()
                            return
                        except Exception as exc:  # fail closed
                            proxy.deny(
                                code="TARGET_VALIDATION_ERROR",
                                message=f"{type(exc).__name__}: {exc}",
                                method=method,
                                url=redirected,
                                navigation=True,
                            )
                            self.send_error(403, "TARGET_VALIDATION_ERROR")
                            self.close_connection = True
                            connection.close()
                            return
                payload = response.read(MAX_RESPONSE_BYTES)
                self.send_response(response.status, response.reason)
                for key, value in response.getheaders():
                    if key.lower() in HOP_BY_HOP_HEADERS:
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if method != "HEAD":
                    self.wfile.write(payload)
                connection.close()
            except OSError as exc:
                self.send_error(502, f"UPSTREAM_FAILED: {type(exc).__name__}")
            self.close_connection = True

        def _tunnel_websocket(self, target, ip: str) -> None:
            port = target.port
            try:
                upstream = socket.create_connection((ip, port), timeout=CONNECT_TIMEOUT_SECONDS)
            except OSError as exc:
                self.send_error(502, f"CONNECT_FAILED: {type(exc).__name__}")
                return
            try:
                # 原样转发请求行（origin-form）与握手头，然后双向隧道。
                path = urlsplit(self.path).path or "/"
                query = urlsplit(self.path).query
                request_line = f"{self.command} {path}{('?' + query) if query else ''} HTTP/1.1\r\n"
                headers = "".join(
                    f"{key}: {value}\r\n"
                    for key, value in self.headers.items()
                    if key.lower() != "proxy-connection"
                )
                upstream.sendall((request_line + headers + "\r\n").encode("utf-8", "ignore"))
                _relay(self.connection, upstream)
            finally:
                try:
                    upstream.close()
                except OSError:
                    pass
            self.close_connection = True

        def do_GET(self):  # noqa: N802
            self._handle_absolute()

        def do_HEAD(self):  # noqa: N802
            self._handle_absolute()

        def do_POST(self):  # noqa: N802
            self._handle_absolute()

        def do_PUT(self):  # noqa: N802
            self._handle_absolute()

        def do_PATCH(self):  # noqa: N802
            self._handle_absolute()

        def do_DELETE(self):  # noqa: N802
            self._handle_absolute()

        def do_OPTIONS(self):  # noqa: N802
            self._handle_absolute()

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return _Handler


__all__ = [
    "BrowserEgressProxy",
    "CONNECT_TIMEOUT_SECONDS",
    "MAX_RESPONSE_BYTES",
    "NEVER_TUNNEL_PORTS",
    "ProxyDenial",
]
