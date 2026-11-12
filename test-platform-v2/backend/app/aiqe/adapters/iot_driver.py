"""M8 / TA-042：硬件 / IoT Driver（单设备协议一套 Adapter，默认只读）。"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

PROTOCOLS = ("mqtt", "http", "serial")
READONLY_OPS = frozenset({"read", "measure", "telemetry", "status"})


class IotError(RuntimeError):
    pass


class IotDriver:
    def __init__(self, protocol: str, transport: Callable[[dict[str, Any]], Any]) -> None:
        if protocol not in PROTOCOLS:
            raise IotError(f"未知 IoT 协议: {protocol}")
        self.protocol = protocol
        self.transport = transport

    def send(self, command: dict[str, Any]) -> Any:
        op = str(command.get("op") or "").lower()
        if not op:
            raise IotError("命令缺少 op")
        if op not in READONLY_OPS:
            raise PermissionError(f"IoT 默认只读，禁止操作: {op}")
        return self.transport(command)

    def read_telemetry(self) -> Any:
        return self.send({"op": "telemetry"})
