"""P1-6 — 平台级 AI 配额闸门与用量台账（app/services/ai_guard.py）。

覆盖：每分钟请求上限 / 24h token 预算 / 未超限放行 / 关闭开关即 no-op /
台账查询失败必须失败关闭 / record 写台账且吞掉 DB 异常 / 网关超限返回 429。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.ai_gateway_app import app as gateway_app
from app.core import config
from app.core.config import Settings
from app.core.db import get_db
from app.modules.aitde.governance.models import ModelUsageLedger
from app.services import ai_client, ai_guard, triage_service


@pytest.fixture(autouse=True)
def _ledger_private_session(monkeypatch, db_session):
    """把 `ai_guard.record` 的**独立会话**指向本测试的内存库。

    record() 自带 `SessionLocal()`、刻意不借用调用方会话（见其 docstring）；
    测试里必须显式指向测试库，否则台账会写到进程默认库而断言看不到。
    """
    monkeypatch.setattr(ai_guard, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    return db_session


# ── 配置默认值 ──────────────────────────────────────────────────

def test_ai_guard_defaults(monkeypatch) -> None:
    for name in ("AI_GUARD_ENABLED", "AI_RATE_LIMIT_PER_MINUTE", "AI_DAILY_TOKEN_BUDGET"):
        monkeypatch.delenv(name, raising=False)
    fresh = Settings(_env_file=None)  # 只看声明默认值，不受本地 .env 覆盖影响
    assert fresh.ai_guard_enabled is True
    assert fresh.ai_rate_limit_per_minute == 60
    assert fresh.ai_daily_token_budget == 2000000


def test_default_rate_cap_admits_one_large_case_generation_burst(
    db_session, monkeypatch
) -> None:
    """默认每分钟上限必须容得下「单次大文档生成用例」的合法突发。

    证据（app/services/ai_service.py）：抽取每 24000 字符一次（_EXTRACT_CHUNK_CHARS）、
    生成每 12 个功能点一块（_CHUNK_FP_LIMIT）、并发 5（_CHUNK_CONCURRENCY），
    块被截断还要重试一次，单次操作可发出 15~30 次调用。上限若压到这个量级之下，
    核心功能会以 429 静默丢失用例（抽取块直接跳过），比"更安全"更糟。
    """
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(
        config.settings,
        "ai_rate_limit_per_minute",
        Settings(_env_file=None).ai_rate_limit_per_minute,
    )
    monkeypatch.setattr(config.settings, "ai_daily_token_budget", 10**9)
    for _ in range(30):
        ai_guard.record(db_session, 7, operation_type="case_generation", input_units=10)

    ai_guard.enforce(db_session, 7, operation_type="case_generation")  # 不应抛错


# ── enforce ────────────────────────────────────────────────────

def test_enforce_passes_under_caps(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 5)
    monkeypatch.setattr(config.settings, "ai_daily_token_budget", 1000)
    ai_guard.record(db_session, 7, operation_type="chat", input_units=10, output_units=5)

    ai_guard.enforce(db_session, 7, operation_type="chat")  # 不应抛错


def test_enforce_raises_when_per_minute_cap_exceeded(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 3)
    monkeypatch.setattr(config.settings, "ai_daily_token_budget", 1000000)
    for _ in range(3):
        ai_guard.record(db_session, 7, operation_type="chat")

    with pytest.raises(ai_guard.AIQuotaExceededError) as exc:
        ai_guard.enforce(db_session, 7, operation_type="chat")
    assert exc.value.reason == "quota_rate"
    assert "3" in exc.value.message and "每分钟上限" in exc.value.message


def test_enforce_raises_when_daily_token_budget_exceeded(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 1000)
    monkeypatch.setattr(config.settings, "ai_daily_token_budget", 100)
    ai_guard.record(db_session, 7, operation_type="chat", input_units=60, output_units=40)

    with pytest.raises(ai_guard.AIQuotaExceededError) as exc:
        ai_guard.enforce(db_session, 7, operation_type="chat")
    assert exc.value.reason == "quota_tokens"
    assert "token 预算" in exc.value.message


def test_enforce_is_scoped_per_project(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 2)
    monkeypatch.setattr(config.settings, "ai_daily_token_budget", 1000000)
    for _ in range(2):
        ai_guard.record(db_session, 7, operation_type="chat")

    with pytest.raises(ai_guard.AIQuotaExceededError):
        ai_guard.enforce(db_session, 7)
    ai_guard.enforce(db_session, 8)  # 其它项目不受影响


def test_enforce_is_noop_when_disabled(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_guard_enabled", False)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 1)
    monkeypatch.setattr(config.settings, "ai_daily_token_budget", 1)
    for _ in range(5):
        ai_guard.record(db_session, 7, operation_type="chat", input_units=100, output_units=100)

    ai_guard.enforce(db_session, 7, operation_type="chat")  # 不应抛错


def test_enforce_fails_closed_when_ledger_query_errors(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 100)

    def _boom(*args, **kwargs):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(ai_guard, "_count_recent_requests", _boom)
    with pytest.raises(ai_guard.AIQuotaExceededError) as exc:
        ai_guard.enforce(db_session, 7, operation_type="chat")
    assert exc.value.reason == "check_failed"
    assert "失败关闭" in exc.value.message


# ── record ─────────────────────────────────────────────────────

def test_record_writes_ledger_row(db_session) -> None:
    ai_guard.record(
        db_session,
        7,
        operation_type="gateway_chat",
        model_ref="deepseek-v4-pro",
        input_units=120,
        output_units=30,
        latency_ms=456,
        cost_amount=0.01,
        mission_id=9,
    )
    row = db_session.query(ModelUsageLedger).filter(ModelUsageLedger.project_id == 7).one()
    assert row.operation_type == "gateway_chat"
    assert row.model_ref == "deepseek-v4-pro"
    assert (row.input_units, row.output_units) == (120, 30)
    assert row.latency_ms == 456
    assert row.mission_id == 9
    assert row.created_at is not None


def test_record_swallows_db_errors(monkeypatch) -> None:
    class _BrokenSession:
        def add(self, *_args, **_kwargs):
            raise RuntimeError("insert failed")

        def commit(self):  # pragma: no cover - add() 已经先抛
            raise RuntimeError("commit failed")

        def rollback(self):
            raise RuntimeError("rollback failed too")

        def close(self):
            raise RuntimeError("close failed too")

    monkeypatch.setattr(ai_guard, "SessionLocal", _BrokenSession)

    # 记账失败不得抛回调用方（否则一次台账故障会打断业务 LLM 调用）
    assert ai_guard.record(None, 7, operation_type="chat") is None


def test_record_never_touches_the_caller_session(db_session) -> None:
    """隔离契约：record 使用独立会话，绝不 add/commit/rollback 调用方会话。

    这条不变量正是为了防「调用方手上还有未提交业务对象时被记账顺手提交」，
    以及网关 `except` 分支里提交半成品状态。
    """

    class _CallerSpy:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def add(self, *_args, **_kwargs):
            self.calls.append("add")

        def commit(self):
            self.calls.append("commit")

        def rollback(self):
            self.calls.append("rollback")

    spy = _CallerSpy()
    ai_guard.record(spy, 7, operation_type="chat", input_units=3, output_units=4)

    assert spy.calls == []
    row = db_session.query(ModelUsageLedger).filter(ModelUsageLedger.project_id == 7).one()
    assert (row.input_units, row.output_units) == (3, 4)


# ── 网关咽喉：429 与记账 ────────────────────────────────────────

def _gateway_client(db_session):
    def override_get_db():
        yield db_session

    gateway_app.dependency_overrides[get_db] = override_get_db
    return TestClient(gateway_app)


def test_gateway_returns_429_when_quota_exceeded(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 1)
    ai_guard.record(db_session, 7, operation_type="seed")

    called: list[int] = []
    monkeypatch.setattr(
        ai_client,
        "chat_completions_full",
        lambda *a, **k: called.append(1) or {"content": "{}"},
    )

    client = _gateway_client(db_session)
    try:
        response = client.post(
            "/internal/ai/v1/chat",
            headers={"X-AI-Gateway-Token": "secret"},
            json={"project_id": 7, "system_prompt": "s", "user_message": "u"},
        )
    finally:
        gateway_app.dependency_overrides.clear()

    assert response.status_code == 429
    assert "每分钟上限" in response.json()["detail"]
    assert called == []  # 被闸门拦下，模型调用根本没发生


def test_gateway_records_usage_from_model_response(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_gateway_token", "secret")
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(
        ai_client,
        "chat_completions_full",
        lambda *a, **k: {
            "content": '{"ok":true}',
            "model_name": "deepseek-v4-pro",
            "usage": {"input_tokens": 11, "output_tokens": 5},
            "duration_ms": 42,
        },
    )

    client = _gateway_client(db_session)
    try:
        response = client.post(
            "/internal/ai/v1/chat",
            headers={"X-AI-Gateway-Token": "secret"},
            json={"project_id": 7, "system_prompt": "s", "user_message": "u"},
        )
    finally:
        gateway_app.dependency_overrides.clear()

    assert response.status_code == 200
    row = db_session.query(ModelUsageLedger).filter(ModelUsageLedger.project_id == 7).one()
    assert row.operation_type == "gateway_chat"
    assert row.model_ref == "deepseek-v4-pro"
    assert (row.input_units, row.output_units) == (11, 5)
    assert row.latency_ms == 42


# ── 绕过网关的直连链路（分诊 httpx）也必须被闸门拦住 ─────────────

def test_triage_direct_llm_call_is_gated(db_session, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "ai_guard_enabled", True)
    monkeypatch.setattr(config.settings, "ai_rate_limit_per_minute", 1)
    ai_guard.record(db_session, 7, operation_type="seed")

    def _no_http(*_args, **_kwargs):
        raise AssertionError("配额已满时不得发起出网 LLM 调用")

    monkeypatch.setattr(httpx, "Client", _no_http)
    monkeypatch.setattr(
        triage_service.ai_config_service,
        "resolve",
        lambda db, project_id: SimpleNamespace(api_base_url="http://x", api_key="k", model="m"),
    )

    classified = [{"case_title": "t", "case_type": "api", "priority": "P1", "result_data": {}}]
    with pytest.raises(ai_guard.AIQuotaExceededError):
        triage_service._llm_deep_analyze(db_session, 7, classified)
