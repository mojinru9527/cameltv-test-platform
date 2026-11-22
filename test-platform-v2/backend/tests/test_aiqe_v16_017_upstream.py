"""TC-AIQE-006：上游 5xx 必须 BLOCKED/UPSTREAM_5XX，不归因产品 FAIL。"""
from __future__ import annotations

from types import SimpleNamespace

from app.aiqe.security.target_policy import PolicyDecision, TargetPolicy
from app.aiqe.services import node_executor


def _policy() -> TargetPolicy:
    return TargetPolicy(
        project_id=1,
        version=1,
        source="policy_record:test",
        allowed_hosts=("127.0.0.1",),
        allowed_ports=(80,),
        allow_private_cidrs=("127.0.0.0/8",),
        decision=PolicyDecision.ALLOW,
    )


def _fake_result():
    return SimpleNamespace(
        ok=False,
        status_code=504,
        response={"status_code": 504, "body": '{"status":504}', "headers": {}},
        request={"method": "GET", "url": "http://127.0.0.1/x"},
        error=None,
        duration_ms=1,
        policy_denied=False,
        error_code="",
    )


def test_upstream_504_is_blocked_not_product_fail(monkeypatch):
    monkeypatch.setattr(
        node_executor.SafeHttpExecutor, "request", lambda self, *a, **k: _fake_result()
    )
    node = SimpleNamespace(node_key="third_party", id="node-1", driver_key="http")
    execution = node_executor._execute_http_secure(
        {
            "url": "http://127.0.0.1:80/x",
            "expected_status": 200,
            "upstream_dependency": True,
        },
        node=node,
        db=None,
        policy=_policy(),
    )
    assert execution.status == "BLOCKED"
    assert execution.error_class == "UPSTREAM_5XX"
    assert execution.detail["upstream_status"] == 504


def test_504_without_upstream_flag_is_status_mismatch(monkeypatch):
    monkeypatch.setattr(
        node_executor.SafeHttpExecutor, "request", lambda self, *a, **k: _fake_result()
    )
    node = SimpleNamespace(node_key="product_api", id="node-2", driver_key="http")
    execution = node_executor._execute_http_secure(
        {"url": "http://127.0.0.1:80/x", "expected_status": 200},
        node=node,
        db=None,
        policy=_policy(),
    )
    assert execution.status == "FAILED"
    assert execution.error_class == "STATUS_MISMATCH"
