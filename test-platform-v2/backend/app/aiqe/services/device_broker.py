"""M8 / TA-039：Mobile Device Broker（真机池，Android 优先）。

iOS 受 C84-1 门禁：未解除前注册/分配一律拒绝。
"""
from __future__ import annotations

from dataclasses import dataclass, field

IOS_ENABLED = False  # C84-1 解除后置 True
PLATFORMS = ("android", "ios")


class DeviceBrokerError(ValueError):
    pass


class PlatformNotEnabled(DeviceBrokerError):
    pass


class NoDeviceAvailable(DeviceBrokerError):
    pass


@dataclass
class Device:
    device_id: str
    platform: str
    status: str = "available"  # available | busy | offline
    capabilities: set[str] = field(default_factory=set)
    appium_port: int | None = None


class DeviceBroker:
    def __init__(self, devices: list[Device] | None = None) -> None:
        self._devices: dict[str, Device] = {}
        for device in devices or []:
            self.register(device)

    def register(self, device: Device) -> Device:
        platform = str(device.platform).lower()
        if platform not in PLATFORMS:
            raise DeviceBrokerError(f"未知平台: {device.platform!r}")
        if platform == "ios" and not IOS_ENABLED:
            raise PlatformNotEnabled("iOS 真机未启用（等待 C84-1 解除）")
        if not str(device.device_id).strip():
            raise DeviceBrokerError("device_id 不能为空")
        if device.device_id in self._devices:
            raise DeviceBrokerError(f"设备重复注册: {device.device_id}")
        device.platform = platform
        self._devices[device.device_id] = device
        return device

    def list_devices(
        self, *, platform: str | None = None, capability: str | None = None
    ) -> list[Device]:
        rows = list(self._devices.values())
        if platform:
            rows = [row for row in rows if row.platform == platform.lower()]
        if capability:
            rows = [row for row in rows if capability in row.capabilities]
        return rows

    def allocate(self, platform: str = "android", *, capabilities: tuple[str, ...] = ()) -> Device:
        platform = platform.lower()
        if platform == "ios" and not IOS_ENABLED:
            raise PlatformNotEnabled("iOS 真机未启用（等待 C84-1 解除）")
        for device in self._devices.values():
            if device.platform != platform or device.status != "available":
                continue
            if all(cap in device.capabilities for cap in capabilities):
                device.status = "busy"
                return device
        raise NoDeviceAvailable(f"无可用 {platform} 设备（capabilities={capabilities}）")

    def release(self, device_id: str) -> Device:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceBrokerError(f"设备不存在: {device_id}")
        if device.status != "busy":
            raise DeviceBrokerError(f"设备未占用: {device_id}")
        device.status = "available"
        return device

    def health(self) -> dict[str, int]:
        result = {"available": 0, "busy": 0, "offline": 0}
        for device in self._devices.values():
            result[device.status] = result.get(device.status, 0) + 1
        return result
