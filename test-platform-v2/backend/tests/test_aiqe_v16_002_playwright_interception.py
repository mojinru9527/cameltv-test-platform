"""V16-002 验收：Playwright 全请求链 TargetPolicy 拦截（真实 Chromium + 受控目标）。

覆盖规格 §V16-002 测试矩阵：
- 主页面导航到允许 host：允许（含真实子资源）；
- 主页面 302 到未授权端口/私网：阻断，**目标服务器收到 0 请求**；
- iframe / 图片 / 脚本 / fetch 到未授权目标：阻断；
- DNS 同时返回公网与私网：拒绝；
- WebSocket 未授权 host：阻断（服务端收到 0 次握手）；
- 新窗口/弹窗导航到不允许 host：阻断；
- 云元数据地址：阻断；
- Service Worker 不参与执行（service_workers=block），route 在 Page 创建前安装。
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.aiqe.drivers.playwright_driver import PlaywrightDriver
from app.aiqe.security.safe_target import SafeTargetValidator
from app.aiqe.security.target_policy import PolicyDecision, TargetPolicy


def _try_chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        try:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
            return True
        finally:
            playwright.stop()
    except Exception:
        return False


CHROMIUM_AVAILABLE = _try_chromium()
requires_chromium = pytest.mark.skipif(
    not CHROMIUM_AVAILABLE,
    reason="BLOCKED: 缺少真实 Chromium Runner（python -m playwright install chromium）",
)


def _policy(*, port: int, host: str = "127.0.0.1", allow_private: bool = True) -> TargetPolicy:
    return TargetPolicy(
        project_id=1,
        version=1,
        source="policy_record:test",
        allowed_hosts=(host,),
        allowed_ports=(port,),
        allow_private_cidrs=("127.0.0.0/8",) if allow_private else (),
        max_redirects=0,
        decision=PolicyDecision.ALLOW,
    )


PAGE_HTML = """<!doctype html><html><head><title>v16-002</title></head><body>
<h1 id="status">READY</h1>
<script src="/ok.js"></script>
<img src="/ok.png"/>
<iframe src="/ok-frame"></iframe>
</body></html>"""

PRIVATE_FETCH_HTML = """<!doctype html><html><head><title>v16-002-denied</title></head><body>
<h1 id="status">READY</h1>
<script>
fetch("http://127.0.0.1:{blocked}/leak").catch(function(){{}});
var img = new Image(); img.src = "http://127.0.0.1:{blocked}/leak-img";
var s = document.createElement('script'); s.src = "http://127.0.0.1:{blocked}/leak.js";
document.head.appendChild(s);
var f = document.createElement('iframe'); f.src = "http://127.0.0.1:{blocked}/leak-frame";
document.body.appendChild(f);
</script>
</body></html>"""

POPUP_HTML = """<!doctype html><html><body>
<a id="pop" href="http://127.0.0.1:{blocked}/leak-popup" target="_blank">open</a>
</body></html>"""

WS_HTML = """<!doctype html><html><body><h1 id="status">READY</h1>
<script>
try {{ new WebSocket("ws://127.0.0.1:{ws_port}/ws"); }} catch (e) {{}}
</script></body></html>"""

SW_HTML = """<!doctype html><html><body><h1 id="status">READY</h1>
<script>
navigator.serviceWorker.register("/sw.js").catch(function(){{}});
</script></body></html>"""


class _TargetState:
    hits: dict[str, int] = {}
    blocked_port = 0
    ws_port = 0


class _TargetHandler(BaseHTTPRequestHandler):
    def _hit(self, path: str) -> None:
        _TargetState.hits[path] = _TargetState.hits.get(path, 0) + 1

    def _html(self, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        self._hit(self.path)
        if self.path == "/ok":
            self._html(PAGE_HTML)
        elif self.path == "/ok.js":
            payload = b"window.__ok = true;"
            self.send_response(200)
            self.send_header("content-type", "application/javascript")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/ok.png":
            payload = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
            )
            self.send_response(200)
            self.send_header("content-type", "image/png")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/ok-frame":
            self._html("<html><body>frame-ok</body></html>")
        elif self.path == "/private-fetch":
            self._html(PRIVATE_FETCH_HTML.format(blocked=_TargetState.blocked_port))
        elif self.path == "/popup":
            self._html(POPUP_HTML.format(blocked=_TargetState.blocked_port))
        elif self.path == "/ws":
            self._html(WS_HTML.format(ws_port=_TargetState.ws_port))
        elif self.path == "/sw":
            self._html(SW_HTML)
        elif self.path == "/sw.js":
            payload = b"self.addEventListener('fetch', function(e) {});"
            self.send_response(200)
            self.send_header("content-type", "application/javascript")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/redirect-blocked":
            self.send_response(302)
            self.send_header("location", f"http://127.0.0.1:{_TargetState.blocked_port}/leak-redirect")
            self.send_header("content-length", "0")
            self.end_headers()
        elif self.path == "/redirect-metadata":
            self.send_response(302)
            self.send_header("location", "http://169.254.169.254/latest/meta-data/")
            self.send_header("content-length", "0")
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header("content-length", "0")
            self.end_headers()

    def log_message(self, *args):
        return


class _BlockedHandler(BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self):  # noqa: N802
        type(self).hits.append(self.path)
        self.send_response(200)
        self.send_header("content-length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        return


class _WsHandler(BaseHTTPRequestHandler):
    handshakes: int = 0

    def do_GET(self):  # noqa: N802
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_response(400)
            self.send_header("content-length", "0")
            self.end_headers()
            return
        type(self).handshakes += 1
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        time.sleep(1.0)

    def log_message(self, *args):
        return


def _serve(handler) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.fixture()
def servers():
    _TargetState.hits = {}
    _BlockedHandler.hits = []
    _WsHandler.handshakes = 0
    target, target_thread = _serve(_TargetHandler)
    blocked, blocked_thread = _serve(_BlockedHandler)
    ws, ws_thread = _serve(_WsHandler)
    _TargetState.blocked_port = blocked.server_address[1]
    _TargetState.ws_port = ws.server_address[1]
    try:
        yield {
            "target_port": target.server_address[1],
            "blocked_port": blocked.server_address[1],
            "ws_port": ws.server_address[1],
            "target": target,
            "blocked": blocked,
            "ws": ws,
        }
    finally:
        for server, thread in ((target, target_thread), (blocked, blocked_thread), (ws, ws_thread)):
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def _run(driver: PlaywrightDriver, spec: dict) -> object:
    try:
        return driver.execute(spec)
    finally:
        driver.close()


def _wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return predicate()


# ── 1. 允许目标：真实导航 + 子资源 ──────────────────────────
@requires_chromium
def test_allowed_navigation_loads_page_and_subresources(servers):
    policy = _policy(port=servers["target_port"])
    driver = PlaywrightDriver(policy=policy, timeout_ms=15000)
    result = _run(driver, {"url": f"http://127.0.0.1:{servers['target_port']}/ok"})

    assert result.status == "SUCCEEDED", (result.error_class, result.error_message)
    assert result.data["title"] == "v16-002"
    assert _TargetState.hits.get("/ok") == 1
    assert _TargetState.hits.get("/ok.js", 0) >= 1
    assert _TargetState.hits.get("/ok.png", 0) >= 1
    assert _TargetState.hits.get("/ok-frame", 0) >= 1
    assert result.data["security_denials"] == []
    assert result.data["target_policy"]["decision"] == "ALLOW"


# ── 2. 主页面目标未授权：不启动浏览器，零请求 ───────────────
@requires_chromium
def test_main_navigation_outside_policy_blocked_before_browser_starts(servers):
    policy = _policy(port=servers["target_port"], host="api.allowed.test")
    driver = PlaywrightDriver(policy=policy, timeout_ms=10000)
    result = _run(driver, {"url": f"http://127.0.0.1:{servers['target_port']}/ok"})

    assert result.status == "BLOCKED"
    assert result.error_class == "HOST_NOT_ALLOWED"
    assert driver._started is False
    assert _TargetState.hits.get("/ok") is None
    denials = result.data["security_denials"]
    assert denials and denials[0]["navigation"] is True


# ── 3. 302 → 未授权端口：阻断且目标零请求 ───────────────────
@requires_chromium
def test_redirect_to_denied_target_blocked_and_never_reached(servers):
    policy = _policy(port=servers["target_port"])
    driver = PlaywrightDriver(policy=policy, timeout_ms=15000)
    result = _run(
        driver, {"url": f"http://127.0.0.1:{servers['target_port']}/redirect-blocked"}
    )
    time.sleep(0.3)

    assert _BlockedHandler.hits == [], "被拒绝的重定向不得抵达目标服务器"
    codes = {item["code"] for item in result.data["security_denials"]}
    assert codes & {"PORT_NOT_ALLOWED", "HOST_NOT_ALLOWED"}, codes
    egress = [item for item in result.data["security_denials"] if item["kind"] == "egress"]
    assert egress, "redirect 必须由出口代理层重新校验并拒绝"
    assert result.status in {"FAILED", "BLOCKED"}


# ── 4. 302 → 云元数据：阻断 ─────────────────────────────────
@requires_chromium
def test_redirect_to_cloud_metadata_blocked(servers):
    # 即使管理员显式把元数据 IP 写进 allowed_hosts，blocked_cidrs 仍必须优先拒绝。
    policy = TargetPolicy(
        project_id=1,
        version=1,
        source="policy_record:test",
        allowed_hosts=("127.0.0.1", "169.254.169.254"),
        allowed_ports=(servers["target_port"], 80),
        allow_private_cidrs=("127.0.0.0/8",),
        decision=PolicyDecision.ALLOW,
    )
    driver = PlaywrightDriver(policy=policy, timeout_ms=15000)
    result = _run(
        driver, {"url": f"http://127.0.0.1:{servers['target_port']}/redirect-metadata"}
    )

    codes = {item["code"] for item in result.data["security_denials"]}
    assert codes & {"ADDRESS_BLOCKED", "PRIVATE_ADDRESS_DENIED", "HOST_NOT_ALLOWED"}, codes
    assert result.status in {"FAILED", "BLOCKED"}
    assert result.data["denied_navigation"] is True


# ── 5. iframe / 图片 / 脚本 / fetch 到未授权目标 ────────────
@requires_chromium
def test_subresource_requests_to_denied_target_blocked(servers):
    policy = _policy(port=servers["target_port"])
    driver = PlaywrightDriver(policy=policy, timeout_ms=15000)
    result = _run(
        driver, {"url": f"http://127.0.0.1:{servers['target_port']}/private-fetch"}
    )
    _wait_for(lambda: len(result.data["security_denials"]) >= 4, timeout=3.0)

    assert _BlockedHandler.hits == [], f"未授权子资源请求抵达目标: {_BlockedHandler.hits}"
    denials = result.data["security_denials"]
    assert len(denials) >= 3, denials
    kinds = {item["resource_type"] for item in denials}
    assert kinds & {"fetch", "image", "script", "document", "egress"}, kinds
    assert all(item["host"] == "127.0.0.1" for item in denials)
    # 只有 iframe；主文档导航本身是允许的，不能被误判成 denied_navigation。
    assert result.data["denied_navigation"] is False


# ── 6. WebSocket 到未授权目标：服务端零握手 ─────────────────
@requires_chromium
def test_websocket_to_denied_target_never_handshakes(servers):
    policy = _policy(port=servers["target_port"])
    driver = PlaywrightDriver(policy=policy, timeout_ms=15000)
    result = _run(driver, {"url": f"http://127.0.0.1:{servers['target_port']}/ws"})
    _wait_for(lambda: _WsHandler.handshakes > 0, timeout=1.5)

    assert _WsHandler.handshakes == 0, "未授权 WebSocket 不得完成握手"
    ws_denials = [
        item
        for item in result.data["security_denials"]
        if item["kind"] in {"websocket", "egress"} and item["host"] == "127.0.0.1"
    ]
    assert ws_denials, result.data["security_denials"]


# ── 7. 弹窗/新窗口导航到未授权目标 ──────────────────────────
@requires_chromium
def test_popup_navigation_to_denied_target_blocked(servers):
    policy = _policy(port=servers["target_port"])
    driver = PlaywrightDriver(policy=policy, timeout_ms=15000)
    result = _run(
        driver,
        {
            "url": f"http://127.0.0.1:{servers['target_port']}/popup",
            "actions": [{"type": "click", "selector": "#pop"}],
        },
    )
    time.sleep(0.8)

    assert _BlockedHandler.hits == [], "弹窗导航不得绕过 route 抵达未授权目标"
    denials = result.data["security_denials"]
    assert any(item["path"] == "/leak-popup" for item in denials), denials


# ── 8. DNS 混合公网/私网：拒绝 ──────────────────────────────
def test_dns_mixed_public_and_private_rejected():
    addresses = [ipaddress.ip_address("93.184.216.34"), ipaddress.ip_address("127.0.0.1")]
    validator = SafeTargetValidator(resolver=lambda host, port: addresses)
    policy = _policy(port=443, host="api.allowed.test", allow_private=False)
    driver = PlaywrightDriver(policy=policy, validator=validator, timeout_ms=5000)
    result = _run(driver, {"url": "https://api.allowed.test/orders"})

    assert result.status == "BLOCKED"
    assert result.error_class == "PRIVATE_ADDRESS_DENIED"
    assert driver._started is False


# ── 9. Service Worker 被禁用 + route 先于 Page 安装 ──────────
class _FakeContext:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.routes: dict[str, object] = {}

    def route(self, pattern, handler):
        self.calls.append(f"route:{pattern}")
        self.routes[pattern] = handler

    def route_web_socket(self, pattern, handler):
        self.calls.append(f"route_ws:{pattern}")

    def new_page(self):
        self.calls.append("new_page")
        return object()

    def tracing(self):
        raise AssertionError("tracing 不应在断言路径调用")


class _FakeBrowser:
    def __init__(self) -> None:
        self.context_kwargs: dict = {}
        self.context = _FakeContext()

    def new_context(self, **kwargs):
        self.context_kwargs = kwargs
        return self.context


def test_route_installed_before_page_and_service_workers_blocked():
    policy = _policy(port=443, host="example.test")
    driver = PlaywrightDriver(policy=policy, timeout_ms=1000)
    assert driver._context_kwargs()["service_workers"] == "block"

    ctx = _FakeContext()
    driver._context = ctx
    driver._install_request_guards()
    assert "route:**/*" in ctx.calls
    ctx.new_page()
    assert ctx.calls[-1] == "new_page"
    # route 必须先于 Page 创建注册。
    assert ctx.calls.index("route:**/*") < ctx.calls.index("new_page")


# ── 10. 静态门禁：Driver 不再接受 Workflow 白名单 ────────────
def test_playwright_driver_has_no_workflow_allowlist_parameter():
    import inspect

    signature = inspect.signature(PlaywrightDriver.__init__)
    assert "policy" in signature.parameters
    assert signature.parameters["policy"].default is inspect.Parameter.empty
    assert "allowed_hosts" not in signature.parameters
    source = inspect.getsource(PlaywrightDriver)
    assert "self.allowed_hosts" not in source
