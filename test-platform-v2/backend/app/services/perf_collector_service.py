"""SoloX 性能采集引擎封装 —— 提供设备发现 / App 列表 / 指标采集 / 进程管理。

SoloX (https://github.com/smart-test-ti/SoloX) 是开源 Android/iOS 实时性能采集工具。
本服务通过 SoloX 的 Python API (AppPerformanceMonitor) 进行封装，提供统一接口。

未安装 SoloX 时自动降级为 Mock 模式，允许在无设备环境下开发和测试。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("perf")

# ── SoloX 可选导入 ──
try:
    from solox.public.apm import AppPerformanceMonitor, initPerformanceService
    from solox.public.common import Devices
    SOLOX_AVAILABLE = True
except ImportError:
    SOLOX_AVAILABLE = False
    logger.warning("solox not installed; perf collector running in MOCK mode")


# ── 指标定义（对标 PerfDog 取值口径）──

METRIC_DEFS: dict[str, dict] = {
    "cpu": {
        "name": "CPU 使用率", "unit": "%",
        "method_android": "/proc/stat + /proc/{pid}/stat",
        "method_ios": "Instruments CPU profiler",
        "threshold": 60.0, "comparator": "<=",
    },
    "memory": {
        "name": "内存使用", "unit": "MB",
        "method_android": "dumpsys meminfo (PSS)",
        "method_ios": "Instruments Memory profiler",
        "threshold": 512.0, "comparator": "<=",
    },
    "fps": {
        "name": "帧率", "unit": "fps",
        "method_android": "SurfaceFlinger / gfxinfo",
        "method_ios": "Instruments Graphics profiler",
        "threshold": 30.0, "comparator": ">=",
    },
    "jank": {
        "name": "卡顿 (Jank)", "unit": "次",
        "method_android": "Choreographer frame callback",
        "method_ios": "Instruments Graphics profiler",
        "threshold": 0.0, "comparator": "<=",
    },
    "startup": {
        "name": "启动耗时", "unit": "ms",
        "method_android": "ActivityManager.getProcessStartTime() + adb am start -W",
        "method_ios": "Instruments Time Profiler",
        "threshold": 2000.0, "comparator": "<=",
    },
    "anr": {
        "name": "ANR / 崩溃", "unit": "次",
        "method_android": "logcat ANR + crashes",
        "method_ios": "MetricKit crashes",
        "threshold": 0.0, "comparator": "<=",
    },
    "battery": {
        "name": "电池", "unit": "level%/temp°C",
        "method_android": "dumpsys battery",
        "method_ios": "IORegistry power diagnostics",
        "threshold": 0.0, "comparator": ">=",
    },
    "network": {
        "name": "网络流量", "unit": "KB/s",
        "method_android": "/proc/{pid}/net/dev",
        "method_ios": "Instruments Network profiler",
        "threshold": 0.0, "comparator": "<=",
    },
}


# ── Mock 数据生成 ──

import math
import random
import time

class MockCollector:
    """无 SoloX / 无设备时的模拟采集器，用于开发调试。"""

    def __init__(self) -> None:
        self._start_ts = time.time()
        self._fps_base = random.uniform(55, 60)
        self._cpu_base = random.uniform(15, 25)
        self._mem_base = random.uniform(200, 350)
        self._jank_count = 0
        self._anr_count = 0

    def snapshot(self) -> dict:
        """生成一次模拟采样。"""
        t = time.time() - self._start_ts
        # 模拟周期性波动
        wave = math.sin(t * 0.3) * 5
        fps = max(5, min(60, self._fps_base + wave + random.uniform(-2, 2)))
        cpu = max(0, min(100, self._cpu_base + wave + random.uniform(-3, 3)))
        mem = max(50, self._mem_base + wave * 3 + random.uniform(-5, 5))

        # 偶发 Jank (5% 概率)
        events = []
        if random.random() < 0.05:
            self._jank_count += 1
            fps = max(5, fps - random.uniform(15, 30))
            events.append({"event_type": "jank", "detail": f"Jank #{self._jank_count}: fps dropped to {fps:.1f}"})

        # 极低概率 ANR (1%)
        if random.random() < 0.01:
            self._anr_count += 1
            events.append({"event_type": "anr", "detail": f"ANR #{self._anr_count}: main thread blocked >5s"})

        return {
            "cpu": {"appCpuRate": round(cpu, 1), "systemCpuRate": round(cpu + random.uniform(5, 15), 1)},
            "memory": {"total": round(mem, 1), "swap": round(random.uniform(0, 10), 1)},
            "fps": {"fps": round(fps, 1), "jank": self._jank_count},
            "battery": {"level": max(60, 100 - int(t / 30)), "temperature": round(28 + random.uniform(0, 8), 1)},
            "network": {"send": round(random.uniform(1, 15), 2), "recv": round(random.uniform(10, 200), 2)},
            "events": events,
        }


# ── 公共接口 ──

def get_connected_devices() -> list[dict[str, Any]]:
    """返回当前连接的 Android/iOS 设备列表。"""
    if not SOLOX_AVAILABLE:
        return _mock_devices()

    try:
        devices = Devices()
        result: list[dict[str, Any]] = []

        # Android 设备
        try:
            android_list = devices.getDevices() or []
        except Exception:
            android_list = []

        for d in android_list:
            device_id = d.get("serial") or d if isinstance(d, str) else str(d)
            result.append({
                "device_id": device_id,
                "device_name": _android_device_name(device_id),
                "device_model": "",
                "platform": "Android",
                "os_version": _android_os_version(device_id),
                "status": "online",
            })

        # iOS 设备
        try:
            ios_list = devices.getDevicesIOS() or []
        except Exception:
            ios_list = []

        for d in ios_list:
            device_id = d.get("udid", "") or d.get("serial", "") or str(d)
            result.append({
                "device_id": device_id,
                "device_name": d.get("name", ""),
                "device_model": d.get("model", ""),
                "platform": "iOS",
                "os_version": d.get("version", ""),
                "status": "online",
            })

        return result
    except Exception as exc:
        logger.error("Failed to get connected devices: %s", exc)
        return []


def get_device_apps(device_id: str, platform: str = "Android") -> list[str]:
    """返回指定设备已安装的应用包名列表。"""
    if not SOLOX_AVAILABLE:
        return _mock_apps()

    try:
        devices = Devices()
        if platform == "iOS":
            raw = devices.getPid(deviceId=device_id, pkgName="")
        else:
            raw = devices.getPid(deviceId=device_id, pkgName="")
        # getPid returns {pid: pkgname} when pkgName is empty
        if isinstance(raw, dict):
            return sorted(set(raw.values()))
        return []
    except Exception as exc:
        logger.error("Failed to list apps on %s: %s", device_id, exc)
        return []


def collect_single_snapshot(device_id: str, pkg_name: str, platform: str = "Android") -> dict:
    """单次采样——返回所有已激活指标的快照数据。"""
    if not SOLOX_AVAILABLE:
        mock = MockCollector()
        return mock.snapshot()

    try:
        apm = AppPerformanceMonitor(
            pkgName=pkg_name,
            platform=platform,
            deviceId=device_id,
            surfaceview=True,
            noLog=True,
        )
        result: dict[str, Any] = {"events": []}
        try:
            result["cpu"] = apm.collectCpu() or {}
        except Exception:
            result["cpu"] = {}
        try:
            result["memory"] = apm.collectMemory() or {}
        except Exception:
            result["memory"] = {}
        try:
            result["fps"] = apm.collectFps() or {}
        except Exception:
            result["fps"] = {}
        try:
            result["battery"] = apm.collectBattery() or {}
        except Exception:
            result["battery"] = {}
        try:
            result["network"] = apm.collectNetwork(wifi=True) or {}
        except Exception:
            result["network"] = {}
        return result
    except Exception as exc:
        logger.error("SoloX snapshot failed: %s", exc)
        raise


def measure_startup_time(device_id: str, pkg_name: str, platform: str = "Android") -> dict:
    """测量 App 冷启动耗时（单位 ms）。Android 通过 adb am start -W。"""
    if not SOLOX_AVAILABLE or platform != "Android":
        return {"startup_ms": random.randint(800, 2500)}

    import subprocess
    try:
        # 先强制停止
        subprocess.run(
            ["adb", "-s", device_id, "shell", "am", "force-stop", pkg_name],
            capture_output=True, timeout=10,
        )
        # 启动并测量
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "am", "start", "-W", f"{pkg_name}/.MainActivity"],
            capture_output=True, text=True, timeout=30,
        )
        total_ms = 0
        for line in result.stdout.splitlines():
            if "TotalTime:" in line:
                total_ms = int(line.split(":")[1].strip())
                break
        return {"startup_ms": total_ms}
    except Exception as exc:
        logger.warning("Startup measurement failed: %s", exc)
        return {"startup_ms": -1}


# ── 内部辅助 ──

def _android_device_name(device_id: str) -> str:
    import subprocess
    try:
        r = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() or device_id
    except Exception:
        return device_id


def _android_os_version(device_id: str) -> str:
    import subprocess
    try:
        r = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.build.version.release"],
            capture_output=True, text=True, timeout=5,
        )
        return f"Android {r.stdout.strip()}" if r.stdout.strip() else ""
    except Exception:
        return ""


def _mock_devices() -> list[dict[str, Any]]:
    return [
        {"device_id": "mock-android-001", "device_name": "Pixel 7 (Mock)", "device_model": "Pixel 7",
         "platform": "Android", "os_version": "Android 14", "status": "online"},
        {"device_id": "mock-ios-001", "device_name": "iPhone 15 Pro (Mock)", "device_model": "iPhone 15 Pro",
         "platform": "iOS", "os_version": "iOS 17.4", "status": "online"},
    ]


def _mock_apps() -> list[str]:
    return [
        "com.cameltv.app",
        "com.cameltv.app.debug",
        "com.example.sportlive",
        "com.google.android.youtube",
    ]
