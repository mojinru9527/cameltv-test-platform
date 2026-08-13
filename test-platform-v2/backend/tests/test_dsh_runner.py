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
