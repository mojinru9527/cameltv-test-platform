"""C70-3 — 登录限流环境化配置（batch-71）。"""
from __future__ import annotations

from app.core.config import Settings


class TestEffectiveLoginRateLimit:
    def test_development_relaxed(self):
        s = Settings(
            environment="development",
            login_rate_limit_max=10,
            login_rate_limit_window_seconds=900,
        )
        max_req, window = s.effective_login_rate_limit
        assert max_req >= 100
        assert window == 900

    def test_test_env_relaxed(self):
        s = Settings(
            environment="test",
            login_rate_limit_max=10,
            login_rate_limit_window_seconds=900,
        )
        max_req, _ = s.effective_login_rate_limit
        assert max_req >= 100

    def test_production_keeps_security_default(self):
        s = Settings(
            environment="production",
            login_rate_limit_max=10,
            login_rate_limit_window_seconds=900,
        )
        assert s.effective_login_rate_limit == (10, 900)

    def test_explicit_override_respected_in_development(self):
        s = Settings(
            environment="development",
            login_rate_limit_max=200,
            login_rate_limit_window_seconds=900,
        )
        max_req, _ = s.effective_login_rate_limit
        assert max_req == 200
