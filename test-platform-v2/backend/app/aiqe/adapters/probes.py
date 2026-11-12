"""P2：真实执行器可用性探针（Appium/minium/pywinauto/MQTT）。"""
from __future__ import annotations

import importlib.util
import os
import shutil
from typing import Any


def probe_appium(url: str, *, client: Any | None = None) -> bool:
    if not url:
        return False
    try:
        if client is None:
            import httpx

            client = httpx.Client(timeout=2)
        response = client.get(f"{url.rstrip('/')}/status")
        return response.status_code == 200
    except Exception:  # 探针失败即不可用
        return False


def command_available(name: str) -> bool:
    return bool(shutil.which(name))


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def collect_probes(env: dict[str, str] | None = None) -> dict[str, Any]:
    resolved = env if env is not None else dict(os.environ)
    appium_url = resolved.get("AIQE_APPIUM_URL", "")
    return {
        "appium_url": appium_url,
        "appium_reachable": probe_appium(appium_url),
        "minium_cli": command_available("minium"),
        "pywinauto": module_available("pywinauto"),
        "paho_mqtt": module_available("paho"),
    }
