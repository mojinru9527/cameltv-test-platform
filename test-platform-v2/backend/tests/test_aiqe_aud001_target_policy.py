"""AUD-001：HTTP SSRF / Redirect / DNS Rebinding 与目标访问策略验收测试。

对应 v1.5 §01 AUD-001「验收测试」逐条：
- loopback / RFC1918 / link-local / 169.254.169.254 / IPv4-mapped IPv6 / 八进制 / 十六进制 /
  整数 IP 全部拒绝；
- 允许域名 302 到未允许私网地址：拒绝且第二个请求不得发出；
- 允许域名 DNS 首次公网、随后变化到私网：拒绝；
- 允许主机、允许端口、GET：正常执行（真实本地服务，非 Mock）；
- Workflow 填写 allow_private / allowed_hosts：忽略并留痕；
- 非法 URL / userinfo / 非 HTTP(S) scheme：拒绝；
- 安全拒绝可追踪 policy version、Run、Node。
"""
from __future__ import annotations

import ipaddress
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.security import (
    SafeHttpExecutor,
    SafeRequest,
    SafeTargetValidator,
    TargetDenied,
    TargetPolicy,
    upsert_target_policy,
)
from app.aiqe.services import event_service, node_executor

GLOBAL_V4 = ipaddress.ip_address("93.184.216.34")
GLOBAL_V6 = ipaddress.ip_address("2606:4700::1111")


def static_resolver(*addresses: str):
    parsed = tuple(ipaddress.ip_address(a) for a in addresses)

    def _resolve(host: str, port: int):
        return parsed

    return _resolve


def open_policy(**overrides) -> TargetPolicy:
    base = {
        "project_id": 1,
        "version": 7,
        "source": "test",
        "allowed_hosts": ("api.allowed.test",),
        "allowed_ports": (80, 443),
        "allowed_methods": ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"),
        "max_redirects": 0,
    }
    base.update(overrides)
    return TargetPolicy(**base)


def validator_with(*addresses: str) -> SafeTargetValidator:
    return SafeTargetValidator(resolver=static_resolver(*addresses))


# ── 1. 私网 / 保留地址 / 混淆写法 ────────────────────────────
BLOCKED_LITERALS = [
    ("http://127.0.0.1/", "PRIVATE_ADDRESS_DENIED"),
    ("http://[::1]/", "PRIVATE_ADDRESS_DENIED"),
    ("http://10.1.2.3/", "PRIVATE_ADDRESS_DENIED"),
    ("http://172.16.5.5/", "PRIVATE_ADDRESS_DENIED"),
    ("http://192.168.1.10/", "PRIVATE_ADDRESS_DENIED"),
    ("http://169.254.169.254/latest/meta-data/", "ADDRESS_BLOCKED"),
    ("http://[::ffff:127.0.0.1]/", "PRIVATE_ADDRESS_DENIED"),
    ("http://[fe80::1]/", "ADDRESS_BLOCKED"),
    ("http://100.64.0.1/", "ADDRESS_BLOCKED"),
    ("http://2130706433/", "AMBIGUOUS_NUMERIC_HOST"),
    ("http://0177.0.0.1/", "AMBIGUOUS_NUMERIC_HOST"),
    ("http://0x7f000001/", "AMBIGUOUS_NUMERIC_HOST"),
    ("http://0x7f.0.0.1/", "AMBIGUOUS_NUMERIC_HOST"),
]


def _host_of(url: str) -> str:
    from urllib.parse import urlsplit

    return urlsplit(url).hostname or ""


@pytest.mark.parametrize(("url", "expected_code"), BLOCKED_LITERALS)
def test_private_and_obfuscated_literals_denied(url, expected_code):
    host = _host_of(url)
    policy = open_policy(allowed_hosts=(host,))
    with pytest.raises(TargetDenied) as excinfo:
        validator_with("93.184.216.34").validate(url, policy)
    assert excinfo.value.code == expected_code


def test_private_cidr_must_be_explicitly_authorized():
    policy = open_policy(allowed_hosts=("127.0.0.1",))
    with pytest.raises(TargetDenied):
        validator_with("127.0.0.1").validate("http://127.0.0.1/health", policy)

    authorized = open_policy(
        allowed_hosts=("127.0.0.1",), allow_private_cidrs=("127.0.0.0/8",)
    )
    target = validator_with("127.0.0.1").validate("http://127.0.0.1/health", authorized)
    assert target.resolved_ips == ("127.0.0.1",)
    assert target.policy_version == 7


def test_blocked_cidr_wins_over_private_authorization():
    policy = open_policy(
        allowed_hosts=("169.254.169.254",), allow_private_cidrs=("169.254.0.0/16",)
    )
    with pytest.raises(TargetDenied) as excinfo:
        validator_with("169.254.169.254").validate("http://169.254.169.254/", policy)
    assert excinfo.value.code == "ADDRESS_BLOCKED"


# ── 2. URL 语法类拒绝 ──────────────────────────────────────
@pytest.mark.parametrize(
    ("url", "expected_code"),
    [
        ("http://user:pass@api.allowed.test/", "USERINFO_NOT_ALLOWED"),
        ("http://user@api.allowed.test/", "USERINFO_NOT_ALLOWED"),
        ("ftp://api.allowed.test/x", "SCHEME_NOT_ALLOWED"),
        ("file:///etc/passwd", "SCHEME_NOT_ALLOWED"),
        ("http://[fe80::1%25eth0]/", "ZONE_ID_NOT_ALLOWED"),
        ("http://api.allowed.test\\@evil.test/", "URL_INVALID"),
        ("http://api.allowed.test /x", "URL_INVALID"),
        ("", "URL_MISSING"),
    ],
)
def test_invalid_urls_denied(url, expected_code):
    policy = open_policy()
    with pytest.raises(TargetDenied) as excinfo:
        validator_with("93.184.216.34").validate(url, policy)
    assert excinfo.value.code == expected_code


# ── 3. 白名单 / 端口 / 方法 ────────────────────────────────
def test_wildcard_host_does_not_match_sibling_domain():
    policy = open_policy(allowed_hosts=("*.example.test",))
    validator = validator_with("93.184.216.34")
    assert validator.validate("https://api.example.test/x", policy).hostname == "api.example.test"
    for host in ("example.test", "evil-example.test", "example.test.evil.io"):
        with pytest.raises(TargetDenied) as excinfo:
            validator.validate(f"https://{host}/x", policy)
        assert excinfo.value.code == "HOST_NOT_ALLOWED"


def test_port_and_method_and_scheme_policy_enforced():
    validator = validator_with("93.184.216.34")
    policy = open_policy(allowed_ports=(443,), allowed_methods=("GET",), allowed_schemes=("https",))
    with pytest.raises(TargetDenied) as excinfo:
        validator.validate("https://api.allowed.test:8443/x", policy)
    assert excinfo.value.code == "PORT_NOT_ALLOWED"
    with pytest.raises(TargetDenied) as excinfo:
        validator.validate("https://api.allowed.test/x", policy, method="DELETE")
    assert excinfo.value.code == "METHOD_NOT_ALLOWED"
    with pytest.raises(TargetDenied) as excinfo:
        validator.validate("http://api.allowed.test/x", policy, method="GET")
    assert excinfo.value.code == "SCHEME_NOT_ALLOWED"


def test_deny_all_policy_denies_everything():
    policy = TargetPolicy.deny_all(project_id=1)
    with pytest.raises(TargetDenied) as excinfo:
        validator_with("93.184.216.34").validate("https://api.allowed.test/", policy)
    assert excinfo.value.code == "HOST_NOT_ALLOWED"
    assert "未配置" in excinfo.value.message


# ── 4. DNS 多地址与 Rebinding ──────────────────────────────
def test_all_resolved_addresses_must_pass():
    policy = open_policy()
    validator = SafeTargetValidator(
        resolver=lambda host, port: {GLOBAL_V4, ipaddress.ip_address("10.0.0.9")}
    )
    with pytest.raises(TargetDenied) as excinfo:
        validator.validate("https://api.allowed.test/x", policy)
    assert excinfo.value.code == "PRIVATE_ADDRESS_DENIED"
    assert excinfo.value.details["ip"] == "10.0.0.9"


def test_dns_rebinding_second_resolution_denied():
    policy = open_policy()
    answers = [(GLOBAL_V4,), (ipaddress.ip_address("127.0.0.1"),)]
    calls = {"n": 0}

    def resolver(host: str, port: int):
        index = min(calls["n"], len(answers) - 1)
        calls["n"] += 1
        return set(answers[index])

    validator = SafeTargetValidator(resolver=resolver)
    first = validator.validate("https://api.allowed.test/x", policy)
    assert first.resolved_ips == ("93.184.216.34",)
    with pytest.raises(TargetDenied) as excinfo:
        validator.validate("https://api.allowed.test/x", policy)
    assert excinfo.value.code == "PRIVATE_ADDRESS_DENIED"


def test_dns_failure_is_denied():
    def failing(host: str, port: int):
        raise TargetDenied("DNS_RESOLUTION_FAILED", "boom")

    with pytest.raises(TargetDenied):
        SafeTargetValidator(resolver=failing).validate(
            "https://api.allowed.test/x", open_policy()
        )


# ── 5. SafeHttpExecutor：真实执行 / Redirect ───────────────
def _mock_executor(handler, *, counter: list[str] | None = None) -> SafeHttpExecutor:
    def factory(policy: TargetPolicy) -> httpx.Client:
        transport = httpx.MockTransport(handler)
        return httpx.Client(transport=transport, follow_redirects=False)

    return SafeHttpExecutor(validator=validator_with("93.184.216.34"), client_factory=factory)


def test_allowed_host_port_get_executes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    executor = _mock_executor(handler)
    result = executor.request(
        SafeRequest("GET", "https://api.allowed.test/health"), open_policy()
    )
    assert result.ok is True
    assert result.status_code == 200
    assert result.request["policy_version"] == 7
    assert result.request["target_resolution_snapshot"]["resolved_ips"] == ["93.184.216.34"]
    assert result.response["body_truncated"] is False


def test_redirect_to_private_address_denied_and_second_request_not_sent():
    """允许域名的 302 指向另一个「已允许域名」，但该域名解析到私网：第二跳必须拒绝。"""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(
                302, headers={"location": "https://internal.allowed.test/admin"}
            )
        return httpx.Response(200, text="should-not-happen")

    def resolver(host: str, port: int):
        if host == "internal.allowed.test":
            return {ipaddress.ip_address("10.9.9.9")}
        return {GLOBAL_V4}

    executor = SafeHttpExecutor(
        validator=SafeTargetValidator(resolver=resolver),
        client_factory=lambda policy: httpx.Client(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ),
    )
    policy = open_policy(
        allowed_hosts=("api.allowed.test", "internal.allowed.test"), max_redirects=3
    )
    result = executor.request(SafeRequest("GET", "https://api.allowed.test/start"), policy)
    assert calls == ["https://api.allowed.test/start"]
    assert result.blocked is True
    assert result.error_code == "PRIVATE_ADDRESS_DENIED"
    assert result.policy_denied is True


def test_redirect_to_unlisted_private_literal_denied_and_not_sent():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
        return httpx.Response(200, text="should-not-happen")

    result = _mock_executor(handler).request(
        SafeRequest("GET", "https://api.allowed.test/start"),
        open_policy(max_redirects=3),
    )
    assert calls == ["https://api.allowed.test/start"]
    assert result.blocked is True
    assert result.error_code in {"HOST_NOT_ALLOWED", "PRIVATE_ADDRESS_DENIED"}


def test_redirect_to_unlisted_host_denied_by_default():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://evil.test/x"})

    result = _mock_executor(handler).request(
        SafeRequest("GET", "https://api.allowed.test/start"), open_policy(max_redirects=2)
    )
    assert calls == ["https://api.allowed.test/start"]
    assert result.blocked is True
    assert result.error_code == "HOST_NOT_ALLOWED"


def test_same_host_redirect_followed_when_policy_allows():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/final"})
        return httpx.Response(200, text="done")

    result = _mock_executor(handler).request(
        SafeRequest("GET", "https://api.allowed.test/start"), open_policy(max_redirects=2)
    )
    assert result.ok is True
    assert len(result.redirect_chain) == 1
    assert result.redirect_chain[0]["to"] == "https://api.allowed.test/final"


def test_redirect_limit_exceeded_blocks():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "/loop"})

    result = _mock_executor(handler).request(
        SafeRequest("GET", "https://api.allowed.test/loop"), open_policy(max_redirects=2)
    )
    assert result.blocked is True
    assert result.error_code == "REDIRECT_LIMIT_EXCEEDED"


def test_307_preserves_method_and_revalidates():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        if request.url.path == "/start":
            return httpx.Response(307, headers={"location": "/final"})
        return httpx.Response(200, text="ok")

    policy = open_policy(max_redirects=2, allowed_methods=("GET", "POST"))
    result = _mock_executor(handler).request(
        SafeRequest("POST", "https://api.allowed.test/start", json_body={"a": 1}), policy
    )
    assert result.ok is True
    assert seen == ["POST", "POST"]


def test_302_rewrites_post_to_get():
    seen: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.content))
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/final"})
        return httpx.Response(200, text="ok")

    policy = open_policy(max_redirects=2, allowed_methods=("GET", "POST"))
    result = _mock_executor(handler).request(
        SafeRequest("POST", "https://api.allowed.test/start", json_body={"a": 1}), policy
    )
    assert result.ok is True
    assert seen[0][0] == "POST"
    assert seen[1] == ("GET", b"")


def test_response_truncated_to_policy_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="x" * 5000)

    result = _mock_executor(handler).request(
        SafeRequest("GET", "https://api.allowed.test/big"),
        open_policy(max_response_bytes=64),
    )
    assert result.ok is True
    assert result.response["body_truncated"] is True
    assert len(result.response["body"]) <= 64


def test_request_body_over_limit_blocked():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - 不应被调用
        raise AssertionError("请求不应发出")

    result = _mock_executor(handler).request(
        SafeRequest("POST", "https://api.allowed.test/x", content=b"y" * 100),
        open_policy(max_request_bytes=10),
    )
    assert result.blocked is True
    assert result.error_code == "REQUEST_TOO_LARGE"


def test_denied_request_never_opens_client():
    def factory(policy: TargetPolicy) -> httpx.Client:  # pragma: no cover
        raise AssertionError("策略拒绝时不得构造客户端")

    executor = SafeHttpExecutor(
        validator=validator_with("93.184.216.34"), client_factory=factory
    )
    result = executor.request(SafeRequest("GET", "http://127.0.0.1/x"), open_policy())
    assert result.blocked is True
    assert result.error_code in {"PRIVATE_ADDRESS_DENIED", "HOST_NOT_ALLOWED"}


# ── 6. 真实本地服务端到端（允许主机 + 允许端口 + GET 正常执行） ──
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 约定
        body = b'{"ok": true, "path": "/health"}'
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # 静默
        return


@pytest.fixture()
def local_http_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_real_local_server_executes_with_explicit_private_authorization(local_http_server):
    port = local_http_server
    policy = open_policy(
        allowed_hosts=("localhost",),
        allowed_ports=(port,),
        allow_private_cidrs=("127.0.0.0/8", "::1/128"),
        max_redirects=0,
        connect_timeout_ms=3000,
        read_timeout_ms=3000,
    )
    result = SafeHttpExecutor().request(
        SafeRequest("GET", f"http://localhost:{port}/health"), policy
    )
    assert result.ok is True, result
    assert result.status_code == 200
    assert '"ok": true' in result.response["body"]
    assert set(result.resolution["resolved_ips"]) <= {"127.0.0.1", "::1"}


def test_real_local_server_blocked_without_private_authorization(local_http_server):
    port = local_http_server
    policy = open_policy(allowed_hosts=("localhost",), allowed_ports=(port,))
    result = SafeHttpExecutor().request(
        SafeRequest("GET", f"http://localhost:{port}/health"), policy
    )
    assert result.blocked is True
    assert result.error_code == "PRIVATE_ADDRESS_DENIED"


# ── 7. 节点执行器：策略强制、覆盖项忽略、安全事件可追踪 ──────
def _seed_run_with_node(db, *, url: str, input_extra: dict | None = None) -> NodeRun:
    run = TestRun(project_id=1, run_key="RUN-AUD001", status="RUNNING")
    db.add(run)
    db.flush()
    node = NodeRun(
        run_id=run.id,
        node_key="api",
        driver_key="http",
        input_ref={"url": url, "method": "GET", **(input_extra or {})},
    )
    db.add(node)
    db.commit()
    return node


def test_node_executor_denies_unlisted_host_and_records_event(db_session):
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["api.allowed.test"], "allowed_ports": [80, 443]},
    )
    node = _seed_run_with_node(db_session, url="http://127.0.0.1/admin")

    outcome = node_executor.execute_node(node, db=db_session)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class == "HOST_NOT_ALLOWED"
    assert outcome.detail["denial"]["code"] == outcome.error_class
    db_session.commit()

    events = event_service.list_events(db_session, node.run_id)
    denied = [e for e in events if e.event_type == "security.target_policy_denied"]
    assert denied, [e.event_type for e in events]
    payload = denied[0].payload_json
    assert payload["policy_version"] == 1
    assert payload["node_key"] == "api"
    assert denied[0].node_run_id == node.id


def test_node_executor_denies_private_address_even_when_host_allowed(db_session):
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["127.0.0.1"], "allowed_ports": [8080]},
    )
    node = _seed_run_with_node(db_session, url="http://127.0.0.1:8080/admin")
    outcome = node_executor.execute_node(node, db=db_session)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class in {"PRIVATE_ADDRESS_DENIED", "ADDRESS_BLOCKED"}


def test_workflow_policy_override_is_ignored(db_session):
    upsert_target_policy(
        db_session,
        project_id=1,
        environment_id=None,
        policy={"allowed_hosts": ["api.allowed.test"], "allowed_ports": [443]},
    )
    node = _seed_run_with_node(
        db_session,
        url="http://127.0.0.1:8080/admin",
        input_extra={"allow_private": True, "allowed_hosts": ["*"], "verify_tls": False},
    )
    outcome = node_executor.execute_node(node, db=db_session)
    db_session.commit()

    assert outcome.status == "BLOCKED"
    assert set(outcome.detail["ignored_overrides"]) == {"allow_private", "allowed_hosts", "verify_tls"}
    events = event_service.list_events(db_session, node.run_id)
    assert any(e.event_type == "security.policy_override_ignored" for e in events)
    assert any(e.event_type == "security.target_policy_denied" for e in events)


def test_node_executor_without_policy_context_blocks():
    node = NodeRun(
        run_id="missing-run",
        node_key="api",
        driver_key="http",
        input_ref={"url": "https://api.allowed.test/x"},
    )
    outcome = node_executor.execute_node(node)
    assert outcome.status == "BLOCKED"
    assert outcome.error_class == "POLICY_UNAVAILABLE"
