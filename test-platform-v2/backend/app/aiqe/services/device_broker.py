"""M8 / TA-039：Mobile Device Broker（真机池，Android 优先）。

iOS 受 C84-1 门禁：未解除前注册/分配一律拒绝。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

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
    runner: str = ""
    device_model: str = ""
    os_version: str = ""
    allocated_at: datetime | None = None
    lease_seconds: int = 300
    last_reason: str = ""


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

    def allocate(
        self,
        platform: str = "android",
        *,
        capabilities: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> Device:
        platform = platform.lower()
        self.reap_expired(now=now)
        if platform == "ios" and not IOS_ENABLED:
            raise PlatformNotEnabled("iOS 真机未启用（等待 C84-1 解除）")
        for device in self._devices.values():
            if device.platform != platform or device.status != "available":
                continue
            if all(cap in device.capabilities for cap in capabilities):
                device.status = "busy"
                device.allocated_at = now or datetime.now(UTC)
                device.last_reason = ""
                return device
        raise NoDeviceAvailable(f"无可用 {platform} 设备（capabilities={capabilities}）")

    def release(self, device_id: str, *, reason: str = "") -> Device:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceBrokerError(f"设备不存在: {device_id}")
        if device.status != "busy":
            raise DeviceBrokerError(f"设备未占用: {device_id}")
        device.status = "available"
        device.allocated_at = None
        device.last_reason = reason
        return device

    def reap_expired(self, *, now: datetime | None = None) -> list[str]:
        """V16-016：租约到期/Worker 崩溃后回收设备，避免永久 busy。"""
        moment = now or datetime.now(UTC)
        released: list[str] = []
        for device in self._devices.values():
            if device.status != "busy" or device.allocated_at is None:
                continue
            expires = device.allocated_at + timedelta(seconds=max(1, int(device.lease_seconds)))
            if expires <= moment:
                device.status = "available"
                device.allocated_at = None
                device.last_reason = "LEASE_EXPIRED"
                released.append(device.device_id)
        return released

    def mark_offline(self, device_id: str, reason: str = "DISCONNECTED") -> Device:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceBrokerError(f"设备不存在: {device_id}")
        device.status = "offline"
        device.allocated_at = None
        device.last_reason = str(reason)[:120]
        return device

    def recover(self, device_id: str) -> Device:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceBrokerError(f"设备不存在: {device_id}")
        if device.status != "offline":
            raise DeviceBrokerError(f"设备不在 offline: {device_id}")
        device.status = "available"
        device.last_reason = "RECOVERED"
        return device

    def health(self) -> dict[str, int]:
        result = {"available": 0, "busy": 0, "offline": 0}
        for device in self._devices.values():
            result[device.status] = result.get(device.status, 0) + 1
        return result
