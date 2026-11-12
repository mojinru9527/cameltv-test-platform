"""M8 / TA-041：Desktop Driver（Electron / Windows UIA / AppleScript）。"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

BACKENDS = ("electron", "windows_uia", "applescript")
OS_BACKEND = {"windows": "windows_uia", "darwin": "applescript", "linux": "electron"}
ACTIONS = ("click", "type", "wait_for", "screenshot")


class DesktopError(RuntimeError):
    pass


def resolve_backend(os_name: str) -> str:
    backend = OS_BACKEND.get(str(os_name).lower())
    if backend is None:
        raise DesktopError(f"不支持的操作系统: {os_name}")
    return backend


@dataclass(frozen=True)
class DesktopAction:
    action: str
    selector: str = ""
    value: str = ""


class DesktopDriver:
    def __init__(self, backend: str, executor: Callable[[DesktopAction], dict[str, Any]]) -> None:
        if backend not in BACKENDS:
            raise DesktopError(f"未知桌面后端: {backend}")
        self.backend = backend
        self.executor = executor

    def execute(self, actions: list[DesktopAction]) -> dict[str, Any]:
        log = []
        error = ""
        for action in actions:
            if action.action not in ACTIONS:
                raise DesktopError(f"未知动作: {action.action}")
            outcome = self.executor(action) or {}
            passed = bool(outcome.get("passed"))
            log.append(
                {
                    "action": action.action,
                    "selector": action.selector,
                    "passed": passed,
                    "evidence": list(outcome.get("evidence") or []),
                }
            )
            if not passed:
                error = str(outcome.get("error") or f"动作失败: {action.action}")
                break
        return {"backend": self.backend, "ok": not error, "error": error, "actions": log}
