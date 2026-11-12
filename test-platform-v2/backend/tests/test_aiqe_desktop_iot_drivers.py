"""M8 / TA-041/042：Desktop + IoT Driver 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.adapters.desktop_driver import (
    DesktopAction,
    DesktopDriver,
    DesktopError,
    resolve_backend,
)
from app.aiqe.adapters.iot_driver import IotDriver, IotError


def ok(action):
    return {"passed": True, "evidence": [f"artifact:{action.action}"]}


def test_resolve_backend_by_os():
    assert resolve_backend("Windows") == "windows_uia"
    assert resolve_backend("darwin") == "applescript"
    assert resolve_backend("linux") == "electron"
    with pytest.raises(DesktopError):
        resolve_backend("plan9")


def test_desktop_execute_success():
    driver = DesktopDriver("windows_uia", ok)
    result = driver.execute(
        [DesktopAction("click", "#publish"), DesktopAction("type", "#title", "hello")]
    )
    assert result["ok"] is True
    assert [item["action"] for item in result["actions"]] == ["click", "type"]


def test_desktop_failure_stops():
    def executor(action):
        if action.action == "click":
            return {"passed": False, "error": "element missing"}
        return {"passed": True}

    result = DesktopDriver("electron", executor).execute(
        [DesktopAction("click", "#a"), DesktopAction("click", "#b")]
    )
    assert result["ok"] is False
    assert "element missing" in result["error"]
    assert len(result["actions"]) == 1


def test_desktop_invalid_backend_and_action():
    with pytest.raises(DesktopError):
        DesktopDriver("qt", ok)
    with pytest.raises(DesktopError):
        DesktopDriver("electron", ok).execute([DesktopAction("drag", "#a")])


def test_iot_protocols_and_readonly():
    assert IotDriver("mqtt", lambda cmd: cmd) is not None
    with pytest.raises(IotError):
        IotDriver("zigbee", lambda cmd: cmd)


def test_iot_telemetry_and_write_rejected():
    driver = IotDriver("http", lambda cmd: {"ok": True, "op": cmd["op"]})
    assert driver.read_telemetry()["op"] == "telemetry"
    with pytest.raises(PermissionError):
        driver.send({"op": "reboot"})
    with pytest.raises(IotError):
        driver.send({})
