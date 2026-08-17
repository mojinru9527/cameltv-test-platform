"""Batch 172 — dsh_runner 单测（mock 运行时，不触真实凭据/网络）。"""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.dsh import dsh_runner
from app.services.dsh.dsh_runner import DshRunResult, runtime_available, run_dsh_task


@pytest.fixture(autouse=True)
def _dsh_off(monkeypatch):
    """默认关闭 DSH，避免污染其他用例。"""
    monkeypatch.setattr(settings, "dsh_enabled", False)
    monkeypatch.setattr(settings, "dsh_api_key", "")
    monkeypatch.setattr(settings, "dsh_runtime", "node")
    yield


def test_runtime_available_disabled(_dsh_off):
    ok, reason = runtime_available()
    assert ok is False
    assert "未启用" in reason


def test_runtime_available_missing_key(_dsh_off, monkeypatch):
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "")
    monkeypatch.setattr(settings, "ai_api_key", "")
    ok, reason = runtime_available()
    assert ok is False
    assert "未配置" in reason


def test_runtime_available_ok(_dsh_off, monkeypatch, tmp_path):
    entry = tmp_path / "bin.js"
    entry.write_text("// dummy", encoding="utf-8")
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "sk-test")
    monkeypatch.setattr(settings, "dsh_runtime", "node")
    monkeypatch.setattr(dsh_runner, "_node_entry", lambda: entry)
    ok, reason = runtime_available()
    assert ok is True
    assert reason == ""


def test_run_empty_task(_dsh_off, monkeypatch):
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "sk-test")
    result = run_dsh_task("   ")
    assert result.exit_code == 2
    assert "为空" in result.error


def test_run_unavailable(_dsh_off, monkeypatch):
    # dsh 关闭 → 快速失败，不触发任何运行时
    result = run_dsh_task("do something")
    assert result.exit_code == 1
    assert "DSH 不可用" in result.error


def test_run_node_mock_success(_dsh_off, monkeypatch, tmp_path):
    entry = tmp_path / "bin.js"
    entry.write_text("// dummy", encoding="utf-8")
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "sk-test")
    monkeypatch.setattr(settings, "dsh_runtime", "node")
    monkeypatch.setattr(dsh_runner, "_node_entry", lambda: entry)

    fake_proc = SimpleNamespace(returncode=0, stdout="hello from dsh\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake_proc)

    result = run_dsh_task("summarize", session_root=str(tmp_path / "sessions"))
    assert isinstance(result, DshRunResult)
    assert result.exit_code == 0
    assert result.final_response == "hello from dsh"
    assert result.error == ""


def test_run_node_mock_timeout(_dsh_off, monkeypatch, tmp_path):
    entry = tmp_path / "bin.js"
    entry.write_text("// dummy", encoding="utf-8")
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "sk-test")
    monkeypatch.setattr(settings, "dsh_runtime", "node")
    monkeypatch.setattr(dsh_runner, "_node_entry", lambda: entry)

    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["node"], timeout=1)

    monkeypatch.setattr(subprocess, "run", _boom)
    result = run_dsh_task("slow task", timeout=1, session_root=str(tmp_path / "sessions"))
    assert result.exit_code == 124
    assert result.timed_out is True
    assert "超时" in result.error


def test_truncate(_dsh_off, monkeypatch):
    monkeypatch.setattr(settings, "dsh_max_output_chars", 10)
    text = "x" * 100
    truncated = dsh_runner._truncate(text)
    assert len(truncated) < 100
    assert "截断" in truncated


# ── Batch 191：团队模式路由 ──

def _node_env(monkeypatch, tmp_path):
    entry = tmp_path / "bin.js"
    entry.write_text("// dummy", encoding="utf-8")
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "sk-test")
    monkeypatch.setattr(settings, "dsh_runtime", "node")
    monkeypatch.setattr(dsh_runner, "_node_entry", lambda: entry)


def test_run_node_team_uses_agent_team_profile(_dsh_off, monkeypatch, tmp_path):
    """mode=team → node cmd 含 --profile agent-team（读 dsh_team_profile）。"""
    _node_env(monkeypatch, tmp_path)
    captured = {}

    def fake_subprocess(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="team done", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_subprocess)
    result = run_dsh_task("团队目标", mode="team", session_root=str(tmp_path / "sessions"))
    assert result.exit_code == 0
    assert captured["cmd"] == ["node", str(tmp_path / "bin.js"), "--profile", "agent-team", "团队目标"]


def test_run_node_team_profile_override(_dsh_off, monkeypatch, tmp_path):
    """dsh_team_profile 可覆盖默认 agent-team。"""
    _node_env(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "dsh_team_profile", "custom-team")
    captured = {}

    def fake_subprocess(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_subprocess)
    run_dsh_task("团队目标", mode="team", session_root=str(tmp_path / "sessions"))
    assert "--profile" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--profile") + 1] == "custom-team"


def test_run_node_team_timeout_uses_team_timeout(_dsh_off, monkeypatch, tmp_path):
    """团队超时：exit 124 + timed_out + 可读 error；DshRunResult 带 workspace。"""
    _node_env(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "dsh_team_timeout_seconds", 0.1)

    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["node"], timeout=0.1)

    monkeypatch.setattr(subprocess, "run", _boom)
    result = run_dsh_task("slow team", mode="team", session_root=str(tmp_path / "sessions"))
    assert result.exit_code == 124
    assert result.timed_out is True
    assert "超时" in result.error
    assert result.workspace  # ws-{uuid} 精确路径回传（终态 team.json 读取用）


def test_run_node_single_unchanged(_dsh_off, monkeypatch, tmp_path):
    """single 行为零变化：profile=headless，workspace 为空。"""
    _node_env(monkeypatch, tmp_path)
    captured = {}

    def fake_subprocess(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="single ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_subprocess)
    result = run_dsh_task("单任务", session_root=str(tmp_path / "sessions"))
    assert captured["cmd"] == ["node", str(tmp_path / "bin.js"), "--profile", "headless", "单任务"]
    assert result.workspace == ""  # single 模式留空（既有断言不回归）


def test_run_team_python_sdk_uses_team_cordis(_dsh_off, monkeypatch, tmp_path):
    """python-sdk 团队分支 → cordis 指向 team.cordis.yml（默认内置）。"""
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "sk-test")
    monkeypatch.setattr(settings, "dsh_runtime", "python-sdk")
    monkeypatch.setattr(settings, "dsh_team_cordis_config", "")

    seen = {}
    import sys
    import types

    class FakeHarness:
        def __init__(self, **kwargs):
            seen["cordis"] = kwargs.get("cordis")
            seen["cwd"] = kwargs.get("cwd")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def run(self, task, session_id=None):
            return SimpleNamespace(final_response="team sdk done")

    fake_mod = types.ModuleType("deepseek_harness")
    fake_mod.DeepSeekHarness = FakeHarness
    monkeypatch.setitem(sys.modules, "deepseek_harness", fake_mod)

    result = run_dsh_task("团队目标", mode="team", session_root=str(tmp_path / "sessions"))
    assert result.exit_code == 0
    assert result.final_response == "team sdk done"
    team_cordis = Path(__file__).resolve().parent.parent / "app" / "services" / "dsh" / "team.cordis.yml"
    assert seen["cordis"] == str(team_cordis)
    assert result.workspace  # SDK 分支同样回传 ws-{uuid}


def test_run_team_python_sdk_custom_cordis(_dsh_off, monkeypatch, tmp_path):
    """dsh_team_cordis_config 可覆盖内置 team.cordis.yml。"""
    monkeypatch.setattr(settings, "dsh_enabled", True)
    monkeypatch.setattr(settings, "dsh_api_key", "sk-test")
    monkeypatch.setattr(settings, "dsh_runtime", "python-sdk")
    custom = tmp_path / "custom.cordis.yml"
    custom.write_text("- id: custom\n", encoding="utf-8")
    monkeypatch.setattr(settings, "dsh_team_cordis_config", str(custom))

    seen = {}
    import sys
    import types

    class FakeHarness:
        def __init__(self, **kwargs):
            seen["cordis"] = kwargs.get("cordis")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def run(self, task, session_id=None):
            return SimpleNamespace(final_response="ok")

    fake_mod = types.ModuleType("deepseek_harness")
    fake_mod.DeepSeekHarness = FakeHarness
    monkeypatch.setitem(sys.modules, "deepseek_harness", fake_mod)

    run_dsh_task("团队目标", mode="team", session_root=str(tmp_path / "sessions"))
    assert seen["cordis"] == str(custom)
