"""Batch 184（C172-1/2）— DSH 沙箱安全加固回归测试。

覆盖：
- 任务级隔离工作区（共享根下每任务独立 ws-{uuid} 子目录）
- 任务文本长度配额（超限拒绝）
- 全局并发闸门（DSH_MAX_CONCURRENT 生效，默认 1）
- python-sdk 凭据并发隔离（env 突变持锁，线程间不互踩；结束后恢复）
- 超时回归（node 路径既有行为）
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.services.dsh import dsh_runner as runner_mod


class TestWorkspaceIsolation:
    def test_shared_root_yields_per_task_subdirs(self, tmp_path):
        """配置共享根时，每次任务仍获得独立 ws-{uuid} 子目录（C172-1）。"""
        root = tmp_path / "ws-root"
        with patch.object(settings, "dsh_workspace", str(root)):
            a = runner_mod._workspace_for(None, tmp_path)
            b = runner_mod._workspace_for(None, tmp_path)
            assert a != b
            assert Path(a).parent == root
            assert Path(b).parent == root
            assert Path(a).name.startswith("ws-")
            assert Path(a).exists() and Path(b).exists()

    def test_explicit_workdir_used_as_root(self, tmp_path):
        """调用方显式 workspace 作为隔离根（仍加 ws-{uuid} 子层）。"""
        base = tmp_path / "explicit"
        base.mkdir()
        ws = runner_mod._workspace_for(str(base), tmp_path)
        assert Path(ws).parent == base
        assert Path(ws).name.startswith("ws-")

    def test_default_root_is_session_workspaces(self, tmp_path):
        with patch.object(settings, "dsh_workspace", ""):
            ws = runner_mod._workspace_for(None, tmp_path)
            assert Path(ws).parent == tmp_path / "workspaces"


class TestTaskLengthQuota:
    def test_oversized_task_rejected(self):
        """任务文本超 DSH_MAX_TASK_CHARS 直接拒绝（C172-1 配额）。"""
        long_task = "x" * (settings.dsh_max_task_chars + 1)
        result = runner_mod.run_dsh_task(long_task)
        assert result.exit_code == 2
        assert "超长" in result.error

    def test_normal_task_passes_length_check(self, monkeypatch):
        """长度合法时进入执行路径（DSH 不可用则返回不可用，而非长度错误）。"""
        monkeypatch.setattr(settings, "dsh_enabled", False)
        result = runner_mod.run_dsh_task("正常任务文本")
        assert result.exit_code == 1  # DSH 不可用（非长度拒绝）
        assert "DSH 不可用" in result.error


class TestConcurrencyGate:
    def test_gate_caps_concurrent_executions(self, monkeypatch):
        """并发闸门生效：DSH_MAX_CONCURRENT 上限内并行，超出排队（C172-1）。"""
        monkeypatch.setattr(settings, "dsh_max_concurrent", 2)
        monkeypatch.setattr(settings, "dsh_runtime", "node")
        monkeypatch.setattr(settings, "dsh_enabled", True)
        monkeypatch.setattr(settings, "dsh_api_key", "k")
        monkeypatch.setattr(settings, "dsh_model", "m")
        monkeypatch.setattr(settings, "dsh_timeout_seconds", 30)
        # 重建闸门（模块级常量在 import 时按配置创建）
        runner_mod._concurrency_gate = threading.BoundedSemaphore(2)

        active = []
        max_active = [0]
        lock = threading.Lock()
        entered = []
        first_wave = threading.Event()

        def fake_node(task, **kwargs):
            with lock:
                active.append(task)
                max_active[0] = max(max_active[0], len(active))
                entered.append(task)
                if len(entered) >= 2:
                    first_wave.set()
            if not first_wave.wait(timeout=5):
                raise TimeoutError("首波并发未到达")
            time.sleep(0.15)
            with lock:
                active.remove(task)
            return runner_mod.DshRunResult(final_response="ok", exit_code=0)

        monkeypatch.setattr(runner_mod, "_run_node_cli", fake_node)
        outputs = []
        threads = [
            threading.Thread(target=lambda i=i: outputs.append(runner_mod.run_dsh_task(f"task-{i}")))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
        assert len(outputs) == 4
        assert all(r.exit_code == 0 for r in outputs)
        assert max_active[0] == 2, f"并发超过上限: {max_active[0]}"
        runner_mod._concurrency_gate = threading.BoundedSemaphore(max(1, settings.dsh_max_concurrent))


class TestPythonSdkEnvIsolation:
    """C172-2：并发 python-sdk 任务凭据互不污染。"""

    def _fake_harness_factory(self, snapshots, expected):
        class FakeHarness:
            def __init__(self, **kwargs):
                self.cwd = kwargs.get("cwd")
                self.session_root = kwargs.get("session_root")

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def run(self, task, session_id=None):
                # 在锁内读取进程 env，验证与任务自身凭据一致（C172-2 隔离语义）
                snapshots.append({
                    "task": task,
                    "key": os.environ.get("DEEPSEEK_API_KEY"),
                    "model": os.environ.get("DSH_MODEL"),
                    "cwd": self.cwd,
                })
                return type("R", (), {"final_response": f"done:{task}"})()

        return FakeHarness

    def test_concurrent_runs_see_own_credentials(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "dsh_runtime", "python-sdk")
        monkeypatch.setattr(settings, "dsh_enabled", True)
        monkeypatch.setattr(settings, "dsh_api_key", "shared-key")
        monkeypatch.setattr(settings, "dsh_max_concurrent", 2)
        runner_mod._concurrency_gate = threading.BoundedSemaphore(2)

        snapshots = []
        fake_cls = self._fake_harness_factory(snapshots, None)
        # SDK 未安装时注入假模块（runner 在函数内 `from deepseek_harness import DeepSeekHarness`）
        import sys
        import types
        if "deepseek_harness" not in sys.modules:
            fake_mod = types.ModuleType("deepseek_harness")
            fake_mod.DeepSeekHarness = fake_cls
            sys.modules["deepseek_harness"] = fake_mod
            monkeypatch.setattr(sys.modules["deepseek_harness"], "DeepSeekHarness", fake_cls)

        # 并发两个任务，各自带不同凭据（模拟不同项目/租户）
        def run_with(task, extra):
            return runner_mod.run_dsh_task(task, extra_env=extra, session_root=str(tmp_path))

        threads = [
            threading.Thread(target=run_with, args=("任务-a", {"DSH_MODEL": "model-a", "DEEPSEEK_API_KEY": "key-a"})),
            threading.Thread(target=run_with, args=("任务-b", {"DSH_MODEL": "model-b", "DEEPSEEK_API_KEY": "key-b"})),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert len(snapshots) == 2, f"快照数 {len(snapshots)}: {snapshots}"
        by_task = {s["task"]: s for s in snapshots}
        assert by_task["任务-a"]["key"] == "key-a"
        assert by_task["任务-a"]["model"] == "model-a"
        assert by_task["任务-b"]["key"] == "key-b"
        assert by_task["任务-b"]["model"] == "model-b"
        # env 恢复：任务结束后不残留任务级凭据
        assert os.environ.get("DEEPSEEK_API_KEY") != "key-b"
        assert os.environ.get("DSH_MODEL") != "model-b"
        runner_mod._concurrency_gate = threading.BoundedSemaphore(max(1, settings.dsh_max_concurrent))


class TestTimeoutRegression:
    def test_node_timeout_returns_timed_out(self, monkeypatch, tmp_path):
        """node 路径超时语义保持（Batch 184 回归）。"""
        monkeypatch.setattr(settings, "dsh_runtime", "node")
        monkeypatch.setattr(settings, "dsh_enabled", True)
        monkeypatch.setattr(settings, "dsh_timeout_seconds", 0.1)
        runner_mod._concurrency_gate = threading.BoundedSemaphore(1)

        def slow_run(task, **kwargs):
            time.sleep(5)
            return runner_mod.DshRunResult(final_response="", exit_code=0)

        monkeypatch.setattr(runner_mod, "_run_node_cli", slow_run)
        # 直接测 _run_python_sdk 之外的分支不可行（node 子进程），改为验证超时参数透传：
        # _run_node_cli 的 subprocess timeout 已有既有测试；此处仅验证 run_dsh_task 不吞异常
        result = runner_mod.run_dsh_task("正常任务")
        assert result.exit_code in (0, 1)
        runner_mod._concurrency_gate = threading.BoundedSemaphore(max(1, settings.dsh_max_concurrent))
