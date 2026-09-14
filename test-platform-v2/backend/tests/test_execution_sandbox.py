"""Security regression tests for subprocess environment isolation."""
from __future__ import annotations

from app.core import execution_sandbox


def test_sandbox_environment_drops_secrets_and_keeps_explicit_values(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "must-not-leak")
    monkeypatch.setenv("DATABASE_URL", "postgresql://leak")
    monkeypatch.setenv("AI_API_KEY", "must-not-leak")
    monkeypatch.setenv("CAMELTV_TARGET_ENV", "test5")

    env = execution_sandbox.sandbox_environment({"BASE_URL": "https://example.test"})

    assert "SECRET_KEY" not in env
    assert "DATABASE_URL" not in env
    assert "AI_API_KEY" not in env
    assert env["CAMELTV_TARGET_ENV"] == "test5"
    assert env["BASE_URL"] == "https://example.test"


def test_execution_process_kwargs_has_explicit_environment(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "must-not-leak")
    kwargs = execution_sandbox.execution_process_kwargs({"BASE_URL": "https://example.test"})
    assert kwargs["env"]["BASE_URL"] == "https://example.test"
    assert "SECRET_KEY" not in kwargs["env"]
