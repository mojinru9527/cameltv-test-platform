"""Production truthfulness contracts for the performance collector."""
from __future__ import annotations

import pytest

from app.services import perf_collector_service as collector


def test_missing_solox_returns_no_synthetic_devices(monkeypatch) -> None:
    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", False)

    assert collector.is_available() is False
    assert collector.get_connected_devices() == []
    assert collector.get_device_apps("missing-device") == []


def test_missing_solox_never_generates_random_metrics(monkeypatch) -> None:
    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", False)

    with pytest.raises(
        collector.CollectorUnavailableError,
        match="真实性能采集",
    ):
        collector.collect_single_snapshot(
            "missing-device",
            "com.example.app",
        )


def test_unsupported_startup_measurement_never_returns_fake_timing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)

    with pytest.raises(
        collector.CollectorUnavailableError,
        match="Android",
    ):
        collector.measure_startup_time(
            "authorized-ios-device",
            "com.example.app",
            platform="iOS",
        )


def test_all_metric_failures_never_create_an_empty_success_snapshot(
    monkeypatch,
) -> None:
    class BrokenMonitor:
        def __init__(self, **_kwargs):
            pass

        def __getattr__(self, _name):
            return lambda **_kwargs: (_ for _ in ()).throw(
                RuntimeError("device disconnected"),
            )

    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)
    monkeypatch.setattr(
        collector,
        "AppPerformanceMonitor",
        BrokenMonitor,
        raising=False,
    )

    with pytest.raises(RuntimeError, match="未返回任何真实性能指标"):
        collector.collect_single_snapshot(
            "disconnected-device",
            "com.example.app",
        )
