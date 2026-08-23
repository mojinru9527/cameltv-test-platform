"""DSH 错误可读性映射（Batch fix）回归测试。

覆盖 harness 原始错误 → 中文提示：模型不存在 / 额度不足 / 401 / 429 / 不匹配原文。
"""
from __future__ import annotations

from app.services.dsh.dsh_task_service import _friendly_error


class TestFriendlyError:
    def test_model_not_exist_mapped(self):
        msg = _friendly_error(
            "dsh: HTTP_422: Model Not Exist: deepseek-v4-flash", "超算互联网"
        )
        assert "deepseek-v4-flash" in msg
        assert "超算互联网" in msg
        assert "HTTP_422" not in msg

    def test_rate_limit_quota_mapped(self):
        msg = _friendly_error(
            "dsh: RATE_LIMIT: Token Plan quota has been exceeded", "scnet"
        )
        assert "额度不足" in msg

    def test_unauthorized_mapped(self):
        msg = _friendly_error("HTTP_401 Unauthorized: invalid api key", "provider-x")
        assert "API Key 无效" in msg

    def test_429_mapped(self):
        msg = _friendly_error("HTTP_429: rate limit reached")
        assert "请求过频" in msg

    def test_unmatched_kept_raw(self):
        raw = "dsh 执行超时（>600s）"
        assert _friendly_error(raw, "provider") == raw

    def test_empty_passthrough(self):
        assert _friendly_error("") == ""
        assert _friendly_error("  ") == ""
