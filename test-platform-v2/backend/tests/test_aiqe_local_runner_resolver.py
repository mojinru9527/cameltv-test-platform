"""v1.4：外部 Runner 变量解析（不把 secret 落库/回传）。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "qa" / "aiqe_local_runner.py"


def _load():
    spec = importlib.util.spec_from_file_location("aiqe_local_runner_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_node_outputs_secret_fixture_env(monkeypatch):
    module = _load()
    monkeypatch.setenv("AIQE_SECRET_API_KEY", "s3cr3t")
    monkeypatch.setenv("BASE_URL", "https://api.test")
    payload = {
        "input": {
            "token": "${nodes.login.outputs.token}",
            "auth": "Bearer ${SECRET:API_KEY}",
            "url": "${ENV:BASE_URL}/x",
            "user": "${FIXTURE:user}",
        },
        "node_outputs": {"login": {"token": "t-1"}},
        "fixtures": {"user": {"name": "qa"}},
    }
    resolved = module.resolve_input(payload)
    assert resolved == {
        "token": "t-1",
        "auth": "Bearer s3cr3t",
        "url": "https://api.test/x",
        "user": {"name": "qa"},
    }


def test_resolve_missing_secret_raises_without_echoing_value(monkeypatch):
    module = _load()
    monkeypatch.delenv("AIQE_SECRET_MISSING", raising=False)
    try:
        module.resolve_input(
            {"input": {"x": "${SECRET:MISSING}"}, "node_outputs": {}, "fixtures": {}}
        )
    except ValueError as exc:
        assert "MISSING" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing secret must fail")
