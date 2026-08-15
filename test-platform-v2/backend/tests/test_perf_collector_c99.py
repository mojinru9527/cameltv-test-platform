"""Batch 185（C99-1-①③）— 并行化采样与 CPU 语义测试。"""
from __future__ import annotations

import time
from unittest.mock import patch

from app.core.config import settings
from app.services import perf_collector_service as svc


class TestParallelSnapshot:
    def test_metrics_collected_in_parallel(self, monkeypatch):
        """五指标并行采集：并发进入数=指标数，单点耗时≈max 而非求和（C99-1-①）。"""
        import threading
        active = []
        max_active = [0]
        lock = threading.Lock()
        slow = 0.3

        def make_tracked(metric):
            def collect(*a, **k):
                with lock:
                    active.append(metric)
                    max_active[0] = max(max_active[0], len(active))
                time.sleep(slow)
                with lock:
                    active.remove(metric)
                return {"ok": True}
            return collect

        monkeypatch.setattr(svc, "SOLOX_AVAILABLE", True)
        # 契约：apm.collectX 访问返回可调用对象（方法），服务统一 collect() 调用
        def make_tracked(metric):
            def collect(*a, **k):
                with lock:
                    active.append(metric)
                    max_active[0] = max(max_active[0], len(active))
                time.sleep(slow)
                with lock:
                    active.remove(metric)
                return {"ok": True}
            return collect

        class FakeAPM:
            def collectCpu(self): return make_tracked("cpu")()

            def collectMemory(self): return make_tracked("memory")()

            def collectFps(self): return make_tracked("fps")()

            def collectBattery(self): return make_tracked("battery")()

            def collectNetwork(self, wifi=False): return make_tracked("network")()

        fake_apm = FakeAPM()
        # 模块级名称在 solox 未安装时不存在 → raising=False 注入
        monkeypatch.setattr(svc, "AppPerformanceMonitor", lambda **kw: fake_apm, raising=False)

        started = time.monotonic()
        result = svc.collect_single_snapshot("dev1", "com.camelrn", "iOS")
        elapsed = time.monotonic() - started

        assert result["cpu"] == {"ok": True}
        assert result["memory"] == {"ok": True}
        assert result["fps"] == {"ok": True}
        assert max_active[0] == 5, f"指标未并行: max_active={max_active[0]}"
        assert elapsed < slow * 2.5, f"采样未并行化: {elapsed:.2f}s"

    def test_single_metric_failure_degrades(self, monkeypatch):
        """单指标失败不影响整体（降级 {} + collection_errors）。"""
        monkeypatch.setattr(svc, "SOLOX_AVAILABLE", True)
        class FakeAPM:
            def collectCpu(self): return {"appCpuRate": 12.3}

            def collectMemory(self): return {"total": 100.0}

            def collectFps(self): return {"fps": 60.0, "jank": 0}

            def collectBattery(self): return {"level": 80}

            def collectNetwork(self, wifi=False):
                raise RuntimeError("boom")

        fake_apm = FakeAPM()
        monkeypatch.setattr(svc, "AppPerformanceMonitor", lambda **kw: fake_apm, raising=False)
        result = svc.collect_single_snapshot("dev1", "com.camelrn", "iOS")
        assert result["cpu"]["appCpuRate"] == 12.3
        assert result["fps"]["fps"] == 60.0
        assert "collection_errors" in result
        assert "network" in result["collection_errors"]


class TestCpuReportMode:
    def _fake_run_with_ticks(self, monkeypatch, tick_delta: int):
        """构造递增 tick 的 adb 假执行：sample1 utime=0,stime=0；sample2 utime=Δ,stime=Δ。"""
        import subprocess
        calls = {"n": 0}

        def stat_line(utime: int, stime: int) -> str:
            return f"123 (proc) S 1 1 1 0 -1 0 0 0 0 0 {utime} {stime} 0 0 20 0 1 0 1000 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"

        def fake_run(*args, **kwargs):
            if "pidof" in args[0]:
                return type("R", (), {"returncode": 0, "stdout": "123\n", "stderr": ""})()
            calls["n"] += 1
            utime = tick_delta if calls["n"] == 2 else 0
            return type("R", (), {"returncode": 0, "stdout": stat_line(utime, utime), "stderr": ""})()

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr("time.sleep", lambda s: None)

    def test_raw_mode_keeps_aggregate_semantics(self, monkeypatch):
        """默认 raw：聚合 CPU 可 >100%（多核如实，行为不变）。"""
        monkeypatch.setattr(settings, "perf_cpu_report_mode", "raw")
        self._fake_run_with_ticks(monkeypatch, tick_delta=50)  # dt=(50+50)/100=1s → 100%
        out = svc._collect_cpu_android("dev1", "com.camelrn")
        assert out["appCpuRate"] == 100.0

    def test_per_core_mode_normalizes(self, monkeypatch):
        """per_core：÷核数（8 核 → 12.5%）。"""
        monkeypatch.setattr(settings, "perf_cpu_report_mode", "per_core")
        monkeypatch.setattr(svc, "_core_count", lambda device_id: 8)
        self._fake_run_with_ticks(monkeypatch, tick_delta=50)  # raw=100 → 100/8=12.5
        out = svc._collect_cpu_android("dev1", "com.camelrn")
        assert out["appCpuRate"] == 12.5

    def test_core_count_parses_possible_range(self, monkeypatch):
        import subprocess
        def fake_run(*args, **kwargs):
            return type("R", (), {"returncode": 0, "stdout": "0-7\n", "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", fake_run)
        assert svc._core_count("dev1") == 8
