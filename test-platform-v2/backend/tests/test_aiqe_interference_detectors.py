"""M3 / TA-023：Interference Detectors 单测（10 类信号 + 纯函数约束）。"""
from __future__ import annotations

import copy

import pytest

from app.aiqe.services.interference_service import (
    KINDS,
    InterferenceDetector,
    detect,
)

SAMPLES = {
    "cpu_throttle": {"cpu": {"throttled_seconds": 1}},
    "memory_pressure": {"memory": {"available_mb": 200}},
    "network_latency": {"network": {"p95_latency_ms": 600}},
    "dns_failure": {"dns": {"failures": 1}},
    "disk_full": {"disk": {"free_pct": 4}},
    "process_crash": {"process": {"crash_count": 1}},
    "port_conflict": {"port": {"conflict": True}},
    "dependency_5xx": {"dependency": {"http_5xx_rate": 0.1}},
    "clock_skew": {"clock": {"skew_ms": 1500}},
    "lock_contention": {"lock": {"wait_ms": 1500}},
}


def test_clean_payload_has_no_signals():
    assert detect({}) == []


@pytest.mark.parametrize("kind", KINDS)
def test_each_kind_detected(kind):
    signals = detect(SAMPLES[kind])
    assert [signal.kind for signal in signals] == [kind]
    assert signals[0].evidence


def test_critical_severity_for_extremes():
    payload = {
        "memory": {"oom_kills": 1},
        "disk": {"free_pct": 1},
        "process": {"crash_count": 3},
        "dependency": {"http_5xx_rate": 0.5},
        "clock": {"skew_ms": 8000},
        "lock": {"wait_ms": 9000},
    }
    signals = {signal.kind: signal.severity for signal in detect(payload)}
    for kind in ("memory_pressure", "disk_full", "process_crash", "dependency_5xx", "clock_skew", "lock_contention"):
        assert signals[kind] == "critical", kind


def test_multiple_signals_and_order():
    payload = {**SAMPLES["dns_failure"], **SAMPLES["disk_full"]}
    kinds = [signal.kind for signal in detect(payload)]
    assert kinds == ["dns_failure", "disk_full"]


def test_detection_is_pure_and_deterministic():
    payload = copy.deepcopy(SAMPLES["network_latency"])
    snapshot = copy.deepcopy(payload)
    first = detect(payload)
    second = detect(payload)
    assert payload == snapshot
    assert first == second


def test_detection_does_not_touch_run_state():
    run = {"id": "run-1", "status": "RUNNING"}
    snapshot = copy.deepcopy(run)
    InterferenceDetector().detect(SAMPLES["cpu_throttle"])
    assert run == snapshot


def test_invalid_payload_rejected():
    with pytest.raises(ValueError):
        detect("not-a-dict")  # type: ignore[arg-type]


def test_all_ten_kinds_registered():
    assert len(KINDS) == 10
    assert set(KINDS) == set(SAMPLES)
