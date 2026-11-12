"""M8 / TA-039：Device Broker 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.services.device_broker import (
    Device,
    DeviceBroker,
    DeviceBrokerError,
    NoDeviceAvailable,
    PlatformNotEnabled,
)


def broker() -> DeviceBroker:
    return DeviceBroker(
        [
            Device("android-1", "android", capabilities={"chrome", "camera"}),
            Device("android-2", "android", capabilities={"chrome"}),
        ]
    )


def test_allocate_and_release():
    instance = broker()
    device = instance.allocate("android", capabilities=("chrome",))
    assert device.status == "busy"
    instance.release(device.device_id)
    assert device.status == "available"


def test_capability_filtering():
    instance = broker()
    device = instance.allocate("android", capabilities=("camera",))
    assert device.device_id == "android-1"


def test_no_device_available():
    instance = DeviceBroker([Device("a", "android", capabilities={"chrome"})])
    instance.allocate("android")
    with pytest.raises(NoDeviceAvailable):
        instance.allocate("android")


def test_ios_gated_by_c84_1():
    with pytest.raises(PlatformNotEnabled):
        DeviceBroker([Device("ios-1", "ios")])
    with pytest.raises(PlatformNotEnabled):
        broker().allocate("ios")


def test_duplicate_and_unknown_platform():
    instance = broker()
    with pytest.raises(DeviceBrokerError):
        instance.register(Device("android-1", "android"))
    with pytest.raises(DeviceBrokerError):
        instance.register(Device("x", "windows"))


def test_health_counts():
    instance = broker()
    instance.allocate("android")
    health = instance.health()
    assert health["busy"] == 1 and health["available"] == 1
