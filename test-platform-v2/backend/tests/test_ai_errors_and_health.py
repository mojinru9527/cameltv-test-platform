"""AI 错误归因与健康态回归（V4.0 生产黑盒复盘 P0-2 / P1-4 / P2-6 / P2-7）。

固化四条生产实测事实，防止回归：
  1. 401 必须归类为 UNAUTHORIZED，并给出「更新密钥」而非「检查 JSON 语法」；
  2. 用户可见错误里**不得**出现服务器本地路径（/tmp/... 或 C:\\...）；
  3. `resolve_out` 必须暴露 health，`configured=True` 不等于可用；
  4. 真正的 JSON 解析失败仍归类为 BAD_RESPONSE，不被 401 分支吃掉。
"""

from __future__ import annotations

import httpx
import pytest

from app.services import ai_errors
from app.services.ai_errors import AiHealthRegistry, ai_health_registry


@pytest.fixture(autouse=True)
def _clean_registry():
    ai_health_registry.reset()
    yield
    ai_health_registry.reset()


# ── 分类 ──


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "HTTPStatusError: Client error '401 Authorization Required' for url "
            "'https://api.deepseek.com/chat/completions'",
            ai_errors.UNAUTHORIZED,
        ),
        ("Client error '403 Forbidden' for url 'https://x/y'", ai_errors.FORBIDDEN),
        ("Client error '429 Too Many Requests'", ai_errors.RATE_LIMITED),
        ("Insufficient Balance", ai_errors.QUOTA),
        ("Client error '404 Not Found' - Model Not Exist", ai_errors.NOT_FOUND),
        ("ReadTimeout: timed out", ai_errors.TIMEOUT),
        ("ConnectError: [Errno -2] Name or service not known", ai_errors.UNREACHABLE),
        ("JSONDecodeError: Expecting value line 1", ai_errors.BAD_RESPONSE),
        ("当前项目未配置 AI 提供方，请在「AI 配置」中添加提供方后重试", ai_errors.UNCONFIGURED),
    ],
)
def test_classify_ai_error(raw: str, expected: str) -> None:
    assert ai_errors.classify_ai_error(raw) == expected


def test_classify_real_httpx_401() -> None:
    """真实 httpx 异常对象（而非字符串）也要正确归类。"""
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(401, request=request)
    exc = httpx.HTTPStatusError("401 Unauthorized", request=request, response=response)
    assert ai_errors.classify_ai_error(exc) == ai_errors.UNAUTHORIZED


# ── 文案 ──


def test_humanize_401_is_actionable_not_json_advice() -> None:
    msg = ai_errors.humanize_ai_error(
        "Client error '401 Authorization Required' for url 'https://api.deepseek.com/chat/completions'",
        "DeepSeek 官方",
    )
    assert "API Key" in msg
    assert "AI 配置" in msg
    assert "DeepSeek 官方" in msg
    # 生产缺陷原文案把 401 说成 JSON 语法错误，必须不再出现
    assert "JSON" not in msg
    assert "语法" not in msg


def test_humanize_strips_server_local_paths() -> None:
    """P1-4：用户可见文案不得泄露服务端路径。"""
    raw = (
        "AI 返回的 JSON 格式异常。原始响应已保存至: /tmp/ai_response_failed_1788270304.json "
        "另见 C:\\srv\\app\\logs\\ai.log"
    )
    detailed = ai_errors.humanize_ai_error(raw, include_detail=True)
    assert "/tmp/ai_response_failed" not in detailed
    assert "C:\\srv\\app\\logs" not in detailed
    assert "<服务端日志>" in detailed


def test_humanize_keeps_endpoint_url_intact() -> None:
    """脱敏不得误伤 URL —— 端点地址是排查所需信息，且不属于内部路径泄露。

    本地验证曾出现 `https://api.deepseek.com/chat/completions` 被吃成
    `https:/<服务端日志>`，诊断价值归零。
    """
    raw = (
        "Client error '401 Unauthorized' for url "
        "'https://api.deepseek.com/chat/completions'. dump: /tmp/ai_x.json"
    )
    detailed = ai_errors.humanize_ai_error(raw, include_detail=True)
    assert "https://api.deepseek.com/chat/completions" in detailed
    assert "/tmp/ai_x.json" not in detailed
    assert "<服务端日志>" in detailed


def test_humanize_without_detail_has_no_raw_error() -> None:
    msg = ai_errors.humanize_ai_error("Client error '429 Too Many Requests'")
    assert "原始错误" not in msg


# ── 健康态登记 ──


def test_registry_defaults_to_unknown_not_ok() -> None:
    """未验证时必须是 unknown —— 不能默认当作可用（P2-6 的核心）。"""
    reg = AiHealthRegistry()
    health = reg.get(1)
    assert health.status == "unknown"
    assert health.to_dict()["status"] == "unknown"


def test_registry_records_failure_with_actionable_message() -> None:
    reg = AiHealthRegistry()
    health = reg.record_failure(
        7, "Client error '401 Authorization Required'", provider_id=3, provider_name="DeepSeek 官方"
    )
    assert health.status == "error"
    assert health.kind == ai_errors.UNAUTHORIZED
    assert "API Key" in health.message
    assert reg.get(7).kind == ai_errors.UNAUTHORIZED
    assert reg.get(7).provider_id == 3
    assert reg.get(7).checked_at


def test_registry_success_clears_error_state() -> None:
    reg = AiHealthRegistry()
    reg.record_failure(1, "401 Unauthorized")
    assert reg.get(1).status == "error"
    reg.record_success(1, provider_id=2)
    assert reg.get(1).status == "ok"
    assert reg.get(1).kind == ""


def test_registry_is_isolated_per_project() -> None:
    reg = AiHealthRegistry()
    reg.record_failure(1, "401 Unauthorized")
    reg.record_success(2)
    assert reg.get(1).status == "error"
    assert reg.get(2).status == "ok"
    assert reg.get(999).status == "unknown"
