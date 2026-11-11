"""M3 / TA-023：Interference Detectors（13 号 §19 TA-023）。

10 类预置故障检测信号；检测为**纯函数**，不写库、不改 Run 状态：

1. cpu_throttle        2. memory_pressure   3. network_latency
4. dns_failure         5. disk_full         6. process_crash
7. port_conflict       8. dependency_5xx    9. clock_skew
10. lock_contention

输入为观测 payload（嵌套 dict，点路径读取），输出 InterferenceSignal 列表。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

KINDS = (
    "cpu_throttle",
    "memory_pressure",
    "network_latency",
    "dns_failure",
    "disk_full",
    "process_crash",
    "port_conflict",
    "dependency_5xx",
    "clock_skew",
    "lock_contention",
)


@dataclass(frozen=True)
class InterferenceSignal:
    kind: str
    severity: str  # warning | critical
    evidence: dict[str, Any]


def _get(payload: dict[str, Any], path: str, default: Any = 0) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _severity(value: float, warning: float, critical: float) -> str:
    return "critical" if value >= critical else "warning"


def cpu_throttle(payload: dict[str, Any]) -> InterferenceSignal | None:
    throttled = float(_get(payload, "cpu.throttled_seconds", 0) or 0)
    usage = float(_get(payload, "cpu.usage_pct", 0) or 0)
    if throttled > 0 or usage >= 95:
        return InterferenceSignal(
            "cpu_throttle",
            _severity(max(throttled, usage), 1, 5),
            {"throttled_seconds": throttled, "usage_pct": usage},
        )
    return None


def memory_pressure(payload: dict[str, Any]) -> InterferenceSignal | None:
    available = float(_get(payload, "memory.available_mb", 4096) or 0)
    oom = int(_get(payload, "memory.oom_kills", 0) or 0)
    if available < 256 or oom > 0:
        return InterferenceSignal(
            "memory_pressure",
            "critical" if available < 128 or oom > 0 else "warning",
            {"available_mb": available, "oom_kills": oom},
        )
    return None


def network_latency(payload: dict[str, Any]) -> InterferenceSignal | None:
    p95 = float(_get(payload, "network.p95_latency_ms", 0) or 0)
    loss = float(_get(payload, "network.packet_loss_pct", 0) or 0)
    if p95 > 500 or loss > 1:
        return InterferenceSignal(
            "network_latency",
            _severity(max(p95, loss * 100), 500, 2000),
            {"p95_latency_ms": p95, "packet_loss_pct": loss},
        )
    return None


def dns_failure(payload: dict[str, Any]) -> InterferenceSignal | None:
    failures = int(_get(payload, "dns.failures", 0) or 0)
    if failures > 0:
        return InterferenceSignal(
            "dns_failure", "critical" if failures >= 3 else "warning", {"failures": failures}
        )
    return None


def disk_full(payload: dict[str, Any]) -> InterferenceSignal | None:
    free = float(_get(payload, "disk.free_pct", 100) or 0)
    if free < 5:
        return InterferenceSignal(
            "disk_full", "critical" if free < 2 else "warning", {"free_pct": free}
        )
    return None


def process_crash(payload: dict[str, Any]) -> InterferenceSignal | None:
    crashes = int(_get(payload, "process.crash_count", 0) or 0)
    if crashes > 0:
        return InterferenceSignal(
            "process_crash", "critical" if crashes >= 2 else "warning", {"crash_count": crashes}
        )
    return None


def port_conflict(payload: dict[str, Any]) -> InterferenceSignal | None:
    conflict = bool(_get(payload, "port.conflict", False))
    bind_errors = int(_get(payload, "port.bind_errors", 0) or 0)
    if conflict or bind_errors > 0:
        return InterferenceSignal(
            "port_conflict", "warning", {"conflict": conflict, "bind_errors": bind_errors}
        )
    return None


def dependency_5xx(payload: dict[str, Any]) -> InterferenceSignal | None:
    rate = float(_get(payload, "dependency.http_5xx_rate", 0) or 0)
    count = int(_get(payload, "dependency.upstream_5xx", 0) or 0)
    if rate > 0.05 or count > 0:
        return InterferenceSignal(
            "dependency_5xx", "critical" if rate > 0.2 else "warning",
            {"http_5xx_rate": rate, "upstream_5xx": count},
        )
    return None


def clock_skew(payload: dict[str, Any]) -> InterferenceSignal | None:
    skew = float(_get(payload, "clock.skew_ms", 0) or 0)
    if abs(skew) > 1000:
        return InterferenceSignal(
            "clock_skew", "critical" if abs(skew) > 5000 else "warning", {"skew_ms": skew}
        )
    return None


def lock_contention(payload: dict[str, Any]) -> InterferenceSignal | None:
    wait = float(_get(payload, "lock.wait_ms", 0) or 0)
    count = int(_get(payload, "lock.contention_count", 0) or 0)
    if wait > 1000 or count > 0:
        return InterferenceSignal(
            "lock_contention", "critical" if wait > 5000 else "warning",
            {"wait_ms": wait, "contention_count": count},
        )
    return None


DETECTORS: dict[str, Callable[[dict[str, Any]], InterferenceSignal | None]] = {
    "cpu_throttle": cpu_throttle,
    "memory_pressure": memory_pressure,
    "network_latency": network_latency,
    "dns_failure": dns_failure,
    "disk_full": disk_full,
    "process_crash": process_crash,
    "port_conflict": port_conflict,
    "dependency_5xx": dependency_5xx,
    "clock_skew": clock_skew,
    "lock_contention": lock_contention,
}


def detect(payload: dict[str, Any]) -> list[InterferenceSignal]:
    """纯函数：只读 payload，不修改入参、不触碰 Run/DB。"""
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是对象")
    return [signal for fn in DETECTORS.values() if (signal := fn(payload)) is not None]


class InterferenceDetector:
    def detect(self, payload: dict[str, Any]) -> list[InterferenceSignal]:
        return detect(payload)
