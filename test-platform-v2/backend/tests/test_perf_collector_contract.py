"""Production truthfulness contracts for the performance collector."""
from __future__ import annotations

import pytest

from app.services import perf_collector_service as collector


def test_missing_solox_returns_no_synthetic_devices(monkeypatch) -> None:
    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", False)

    assert collector.is_available() is False
    assert collector.get_connected_devices() == []
    assert collector.get_device_apps("missing-device") == []


def test_solox_string_device_list_is_parsed(monkeypatch) -> None:
    """SoloX getDevices() 返回 ['dcd8891f(PEDM00)'] 字符串，必须解析为设备对象。"""
    class FakeDevices:
        def getDevices(self):
            return ["dcd8891f(PEDM00)"]

    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)
    monkeypatch.setattr(collector, "Devices", lambda: FakeDevices())
    monkeypatch.setattr(collector, "_android_device_name", lambda _device_id: "OPPO Find X3")
    monkeypatch.setattr(collector, "_android_os_version", lambda _device_id: "Android 14")

    devices = collector.get_connected_devices()
    assert len(devices) == 1
    assert devices[0]["device_id"] == "dcd8891f"
    assert devices[0]["device_model"] == "PEDM00"
    assert devices[0]["device_name"] == "OPPO Find X3"
    assert devices[0]["os_version"] == "Android 14"
    assert devices[0]["platform"] == "Android"
    assert devices[0]["status"] == "online"


def test_solox_dict_device_list_is_supported(monkeypatch) -> None:
    class FakeDevices:
        def getDevices(self):
            return [{"serial": "serial-1", "model": "Pixel"}]

    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)
    monkeypatch.setattr(collector, "Devices", lambda: FakeDevices())
    monkeypatch.setattr(collector, "_android_device_name", lambda _device_id: "Pixel")
    monkeypatch.setattr(collector, "_android_os_version", lambda _device_id: "Android 15")

    devices = collector.get_connected_devices()
    assert devices[0]["device_id"] == "serial-1"
    assert devices[0]["device_model"] == "Pixel"


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
