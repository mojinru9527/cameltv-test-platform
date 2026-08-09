"""SoloX 性能采集引擎封装 —— 提供设备发现 / App 列表 / 指标采集 / 进程管理。

SoloX (https://github.com/smart-test-ti/SoloX) 是开源 Android/iOS 实时性能采集工具。
本服务通过 SoloX 的 Python API (AppPerformanceMonitor) 进行封装，提供统一接口。

未安装 SoloX 时明确报告采集器不可用，不生成或返回伪造性能数据。
"""
from __future__ import annotations

import logging
import re
import subprocess
from typing import Any

logger = logging.getLogger("perf")

# ── SoloX 可选导入 ──
try:
    from solox.public.apm import AppPerformanceMonitor
    from solox.public.common import Devices
    SOLOX_AVAILABLE = True
except ImportError:
    SOLOX_AVAILABLE = False
    logger.warning("solox not installed; real performance collection is unavailable")


class CollectorUnavailableError(RuntimeError):
    """Raised when a real device collector is required but unavailable."""


ADB_COMMAND_TIMEOUT_SECONDS = 3.0


def _run_adb(
    adb_path: str,
    *args: str,
    timeout: float = ADB_COMMAND_TIMEOUT_SECONDS,
) -> str:
    """Run the bundled ADB directly with a hard timeout and no shell wrapper."""
    completed = subprocess.run(
        [adb_path, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return completed.stdout


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


# ── 公共接口 ──

def is_available() -> bool:
    """Return whether the real SoloX collector can be used."""
    return SOLOX_AVAILABLE


def get_connected_devices() -> list[dict[str, Any]]:
    """返回当前连接的 Android/iOS 设备列表。"""
    if not SOLOX_AVAILABLE:
        return []

    try:
        devices = Devices()
        result: list[dict[str, Any]] = []

        # SoloX 的 getDevices() 内部使用无超时 os.popen；直接调用其内置 ADB，
        # 防止无设备/ADB 异常时留下永久等待的 shell 子进程。
        try:
            adb_path = str(getattr(devices, "adb", "adb"))
            android_output = _run_adb(
                adb_path,
                "devices",
                "-l",
                timeout=ADB_COMMAND_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Android device discovery failed: %s", exc)
            android_output = ""

        for line in android_output.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) < 2 or parts[1] != "device":
                continue
            device_id = parts[0]
            attributes = {
                key: value
                for token in parts[2:]
                if ":" in token
                for key, value in [token.split(":", 1)]
            }
            model = attributes.get("model", "")
            result.append({
                "device_id": device_id,
                "device_name": _android_device_name(device_id, adb_path),
                "device_model": model,
                "platform": "Android",
                "os_version": _android_os_version(device_id, adb_path),
                "status": "online",
            })

        # iOS 设备
        try:
            get_devices_ios = getattr(devices, "getDeviceInfoByiOS", None)
            ios_list = get_devices_ios() if get_devices_ios else []
        except Exception as exc:
            logger.warning("iOS device discovery failed: %s", exc)
            ios_list = []

        for d in ios_list:
            device_id = (
                d.get("udid", "") or d.get("serial", "") or str(d)
                if isinstance(d, dict)
                else str(d)
            )
            result.append({
                "device_id": device_id,
                "device_name": d.get("name", device_id) if isinstance(d, dict) else device_id,
                "device_model": d.get("model", "") if isinstance(d, dict) else "",
                "platform": "iOS",
                "os_version": d.get("version", "") if isinstance(d, dict) else "",
                "status": "online",
            })

        return result
    except Exception as exc:
        logger.error("Failed to get connected devices: %s", exc)
        return []


def get_device_apps(device_id: str, platform: str = "Android") -> list[str]:
    """返回指定设备已安装的应用包名列表。"""
    if not SOLOX_AVAILABLE:
        return []

    try:
        devices = Devices()
        if platform == "iOS":
            raw = devices.getPkgnameByiOS(device_id) or []
        else:
            adb_path = str(getattr(devices, "adb", "adb"))
            output = _run_adb(
                adb_path,
                "-s",
                device_id,
                "shell",
                "pm",
                "list",
                "packages",
                "--user",
                "0",
                timeout=ADB_COMMAND_TIMEOUT_SECONDS,
            )
            raw = [
                line.removeprefix("package:").strip()
                for line in output.splitlines()
                if line.startswith("package:")
            ]
        return sorted({str(package).strip() for package in raw if str(package).strip()})
    except Exception as exc:
        logger.error("Failed to list apps on %s: %s", device_id, exc)
        return []


def _parse_surfaceflinger_latency(raw: str) -> dict[str, Any]:
    """解析 `dumpsys SurfaceFlinger --latency <layer>` 输出为 fps/jank。

    Android 12+ 首行可能为 `---- TIME: <ts> ----` 头（SoloX 2.9.3 因此解析崩溃），
    必须跳过；随后首个数字行为刷新周期（ns），后续每行 3 个时间戳
    （desired / actual / ready，均为 ns）。
    fps = 最近 1 秒窗口内实际提交帧数；jank = 连续帧间隔 > 2×刷新周期
    且 < 500ms（排除空闲/前后台切换边界）的次数，对标 PerfDog 卡顿口径。
    """
    lines = [
        ln.strip()
        for ln in raw.splitlines()
        if ln.strip() and not ln.strip().startswith("----")
    ]
    refresh_ns = 0.0
    if lines:
        try:
            refresh_ns = float(lines[0])
        except ValueError:
            return {"fps": 0, "jank": 0, "error": "bad refresh period"}

    frames: list[int] = []
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) >= 2:
            try:
                ts = int(parts[1])  # actualPresentTime
                if ts > 0:
                    frames.append(ts)
            except ValueError:
                continue
    if not frames or refresh_ns <= 0:
        return {"fps": 0, "jank": 0, "error": "no frame data"}

    latest = max(frames)
    window = [ts for ts in frames if latest - 1_000_000_000 <= ts <= latest]
    fps = round(len(window), 1)

    ordered = sorted(window)
    jank = 0
    for prev, curr in zip(ordered, ordered[1:]):
        delta = curr - prev
        if 0 < delta < 500_000_000 and delta > refresh_ns * 2.0:
            jank += 1
    return {
        "fps": fps,
        "jank": jank,
        "refresh_ns": refresh_ns,
        "frame_count": len(frames),
    }


def _collect_fps_android(device_id: str, pkg_name: str) -> dict[str, Any]:
    """Android 帧率采集（自实现，规避 SoloX 对 Android 14 SurfaceFlinger 输出解析缺陷）。"""
    import subprocess

    try:
        layers_res = subprocess.run(
            ["adb", "-s", device_id, "shell", "dumpsys", "SurfaceFlinger", "--list"],
            capture_output=True, text=True, timeout=15,
        )
        if layers_res.returncode != 0:
            raise RuntimeError(
                f"fps 图层查询失败（设备不可达？）: {layers_res.stderr.strip() or layers_res.stdout.strip()}"
            )
        layers = layers_res.stdout.splitlines()
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        logger.warning("SurfaceFlinger latency query failed: %s", exc)
        raise RuntimeError(f"fps 采集失败: {exc}") from exc

    candidates = _select_fps_layers(layers, pkg_name)
    if not candidates:
        candidates = [pkg_name]

    last_error = "no frame data in any layer"
    for layer in candidates:
        try:
            out_res = subprocess.run(
                # 图层名可能含括号/空格（如 SurfaceView[...](...)），必须整体加引号交给 adb shell
                ["adb", "-s", device_id, "shell", f"dumpsys SurfaceFlinger --latency '{layer}'"],
                capture_output=True, text=True, timeout=15,
            )
            if out_res.returncode != 0:
                raise RuntimeError(
                    f"fps 延迟数据查询失败: {out_res.stderr.strip() or out_res.stdout.strip()}"
                )
            out = out_res.stdout
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            last_error = str(exc)
            continue
        parsed = _parse_surfaceflinger_latency(out)
        if parsed.get("frame_count", 0) > 0 or "error" not in parsed:
            parsed["layer"] = layer
            return parsed
        last_error = parsed.get("error", "no frame data in any layer")
    return {"fps": 0, "jank": 0, "layer": candidates[0], "error": last_error}


def _parse_dumpsys_meminfo(raw: str) -> float | None:
    """解析 `dumpsys meminfo <pkg>` 的 TOTAL PSS（kB → MB）。"""
    m = re.search(r"TOTAL PSS:\s*(\d+)", raw)
    if not m:
        return None
    return round(int(m.group(1)) / 1024.0, 2)


def _collect_cpu_android(device_id: str, pkg_name: str) -> dict[str, Any]:
    """Android CPU 采集（/proc/<pid>/stat 1 秒双采样，按包汇总多进程）。"""
    import subprocess
    import time

    def sh(*args: str) -> str:
        r = subprocess.run(
            ["adb", "-s", device_id, "shell", *args],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode != 0:
            raise RuntimeError(f"cpu 采集失败: {r.stderr.strip() or r.stdout.strip()}")
        return r.stdout

    def pids() -> list[str]:
        out = sh("pidof", pkg_name).strip()
        return [p for p in out.split() if p.isdigit()]

    def sample() -> dict[str, tuple[int, int]]:
        acc: dict[str, tuple[int, int]] = {}
        for pid in pids():
            try:
                stat = sh("cat", f"/proc/{pid}/stat").strip()
                idx = stat.rfind(")")
                fields = stat[idx + 2:].split()
                acc[pid] = (int(fields[11]), int(fields[12]))  # utime, stime
            except Exception:
                continue
        return acc

    a = sample()
    time.sleep(1.0)
    b = sample()
    hz = 100  # Android CLK_TCK
    total = 0.0
    for pid, (u1, s1) in a.items():
        if pid in b:
            u2, s2 = b[pid]
            dt = (u2 - u1 + s2 - s1) / hz
            if dt > 0:
                total += dt
    # total 为 1 秒窗口内的 CPU 秒数；换算为百分比（多线程/多核可 >100%，如实上报）
    return {"appCpuRate": round(total * 100.0, 2)}


def _collect_memory_android(device_id: str, pkg_name: str) -> dict[str, Any]:
    """Android 内存采集（dumpsys meminfo TOTAL PSS，MB）。"""
    import subprocess

    res = subprocess.run(
        ["adb", "-s", device_id, "shell", "dumpsys", "meminfo", pkg_name],
        capture_output=True, text=True, timeout=15,
    )
    if res.returncode != 0:
        raise RuntimeError(f"memory 采集失败: {res.stderr.strip() or res.stdout.strip()}")
    total_mb = _parse_dumpsys_meminfo(res.stdout)
    if total_mb is None:
        raise RuntimeError("memory 采集失败: 未找到 TOTAL PSS")
    return {"total": total_mb}


def _select_fps_layers(layers: list[str], pkg_name: str) -> list[str]:
    """从 SurfaceFlinger --list 输出中选择可用于帧率采集的图层。

    排除输入透传层（InputSink）与 ActivityRecord 壳层；真实渲染层通常形如
    `com.camelrn/com.camelrn.MainActivity#NNN`。
    """
    return [
        ln.strip()
        for ln in layers
        if pkg_name.lower() in ln.lower()
        and "InputSink" not in ln
        and "ActivityRecord{" not in ln
    ]


def collect_single_snapshot(device_id: str, pkg_name: str, platform: str = "Android") -> dict:
    """单次采样——返回所有已激活指标的快照数据。"""
    if not SOLOX_AVAILABLE:
        raise CollectorUnavailableError(
            "SoloX 未安装，无法执行真实性能采集",
        )

    try:
        apm = AppPerformanceMonitor(
            pkgName=pkg_name,
            platform=platform,
            deviceId=device_id,
            surfaceview=True,
            noLog=True,
        )
        result: dict[str, Any] = {"events": []}
        failures: dict[str, str] = {}
        collectors = {
            "cpu": (
                lambda: _collect_cpu_android(device_id, pkg_name)
                if platform == "Android"
                else apm.collectCpu
            ),
            "memory": (
                lambda: _collect_memory_android(device_id, pkg_name)
                if platform == "Android"
                else apm.collectMemory
            ),
            "fps": (
                lambda: _collect_fps_android(device_id, pkg_name)
                if platform == "Android"
                else apm.collectFps
            ),
            "battery": apm.collectBattery,
            "network": lambda: apm.collectNetwork(wifi=True),
        }
        for metric, collect in collectors.items():
            try:
                result[metric] = collect() or {}
            except Exception as exc:
                logger.warning("SoloX %s collection failed: %s", metric, exc)
                result[metric] = {}
                failures[metric] = str(exc)

        populated = any(result[name] for name in collectors)
        if not populated:
            detail = "; ".join(
                f"{name}: {message}" for name, message in failures.items()
            )
            raise RuntimeError(
                f"SoloX 未返回任何真实性能指标{': ' + detail if detail else ''}",
            )
        if failures:
            result["collection_errors"] = failures
        return result
    except Exception as exc:
        logger.error("SoloX snapshot failed: %s", exc)
        raise


def measure_startup_time(device_id: str, pkg_name: str, platform: str = "Android") -> dict:
    """测量 App 冷启动耗时（单位 ms）。Android 通过 adb am start -W。"""
    if not SOLOX_AVAILABLE:
        raise CollectorUnavailableError(
            "SoloX 未安装，无法执行真实启动耗时测量",
        )
    if platform != "Android":
        raise CollectorUnavailableError(
            "当前仅支持 Android 真实启动耗时测量",
        )

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

def _android_device_name(device_id: str, adb_path: str = "adb") -> str:
    try:
        output = _run_adb(
            adb_path,
            "-s",
            device_id,
            "shell",
            "getprop",
            "ro.product.model",
            timeout=ADB_COMMAND_TIMEOUT_SECONDS,
        )
        return output.strip() or device_id
    except Exception:
        return device_id


def _android_os_version(device_id: str, adb_path: str = "adb") -> str:
    try:
        output = _run_adb(
            adb_path,
            "-s",
            device_id,
            "shell",
            "getprop",
            "ro.build.version.release",
            timeout=ADB_COMMAND_TIMEOUT_SECONDS,
        )
        return f"Android {output.strip()}" if output.strip() else ""
    except Exception:
        return ""
