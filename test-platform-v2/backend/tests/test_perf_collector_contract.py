"""Production truthfulness contracts for the performance collector."""
from __future__ import annotations

import pytest

from app.services import perf_collector_service as collector


def test_missing_solox_returns_no_synthetic_devices(monkeypatch) -> None:
    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", False)

    assert collector.is_available() is False
    assert collector.get_connected_devices() == []
    assert collector.get_device_apps("missing-device") == []


def test_android_device_discovery_uses_bounded_adb(monkeypatch) -> None:
    calls = []

    class FakeDevices:
        adb = "bundled-adb"

        def getDeviceInfoByiOS(self):
            return []

    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)
    monkeypatch.setattr(collector, "Devices", lambda: FakeDevices(), raising=False)
    monkeypatch.setattr(
        collector,
        "_run_adb",
        lambda adb_path, *args, timeout: (
            calls.append((adb_path, args, timeout)),
            (
                "List of devices attached\n"
                "dcd8891f device product:foo model:PEDM00 transport_id:1\n"
                "offline-1 offline transport_id:2\n"
            )
            if args == ("devices", "-l")
            else "OPPO Find X3\n"
            if args[-1] == "ro.product.model"
            else "14\n",
        )[1],
    )

    devices = collector.get_connected_devices()
    assert len(devices) == 1
    assert devices[0]["device_id"] == "dcd8891f"
    assert devices[0]["device_model"] == "PEDM00"
    assert devices[0]["device_name"] == "OPPO Find X3"
    assert devices[0]["os_version"] == "Android 14"
    assert devices[0]["platform"] == "Android"
    assert devices[0]["status"] == "online"
    assert calls[0] == (
        "bundled-adb",
        ("devices", "-l"),
        collector.ADB_COMMAND_TIMEOUT_SECONDS,
    )


def test_ios_device_discovery_uses_actual_solox_method(monkeypatch) -> None:
    class FakeDevices:
        adb = "bundled-adb"

        def getDeviceInfoByiOS(self):
            return ["ios-udid-1"]

    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)
    monkeypatch.setattr(collector, "Devices", lambda: FakeDevices(), raising=False)
    monkeypatch.setattr(collector, "_run_adb", lambda *_args, **_kwargs: "")

    devices = collector.get_connected_devices()
    assert devices == [{
        "device_id": "ios-udid-1",
        "device_name": "ios-udid-1",
        "device_model": "",
        "platform": "iOS",
        "os_version": "",
        "status": "online",
    }]


def test_android_app_list_uses_package_command(monkeypatch) -> None:
    class FakeDevices:
        adb = "bundled-adb"

    calls = []
    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)
    monkeypatch.setattr(collector, "Devices", lambda: FakeDevices(), raising=False)
    monkeypatch.setattr(
        collector,
        "_run_adb",
        lambda adb_path, *args, timeout: (
            calls.append((adb_path, args, timeout)),
            "package:com.example.z\npackage:com.example.a\npackage:com.example.a\n",
        )[1],
    )

    assert collector.get_device_apps("serial-1") == [
        "com.example.a",
        "com.example.z",
    ]
    assert calls == [(
        "bundled-adb",
        ("-s", "serial-1", "shell", "pm", "list", "packages", "--user", "0"),
        collector.ADB_COMMAND_TIMEOUT_SECONDS,
    )]


def test_ios_app_list_uses_installed_package_api(monkeypatch) -> None:
    class FakeDevices:
        def getPkgnameByiOS(self, device_id):
            assert device_id == "ios-udid-1"
            return ["com.example.z", "com.example.a", "com.example.a"]

    monkeypatch.setattr(collector, "SOLOX_AVAILABLE", True)
    monkeypatch.setattr(collector, "Devices", lambda: FakeDevices(), raising=False)

    assert collector.get_device_apps("ios-udid-1", "iOS") == [
        "com.example.a",
        "com.example.z",
    ]


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
