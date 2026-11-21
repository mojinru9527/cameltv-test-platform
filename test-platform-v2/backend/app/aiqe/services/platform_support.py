"""V16-016：多端能力边界（GA 支持清单 / 动作粒度 / 未验证平台不得宣称 VERIFIED）。"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

GA_SUPPORTED = frozenset({"web"})
BLOCKED_PLATFORMS = frozenset({"ios", "miniapp", "desktop", "iot"})
ALL_PLATFORMS = frozenset({"web", "android", "ios", "miniapp", "desktop", "iot"})

#: 每个平台声明支持的动作粒度；未列出的动作在 Preflight 必须 BLOCKED。
PLATFORM_ACTIONS: dict[str, frozenset[str]] = {
    "web": frozenset(
        {
            "navigate",
            "click",
            "input",
            "screenshot",
            "assert",
            "evaluate",
            "wait",
            "upload",
            "download",
            "cleanup",
        }
    ),
    "android": frozenset(
        {
            "install",
            "launch",
            "permission",
            "click",
            "input",
            "screenshot",
            "performance",
            "cleanup",
        }
    ),
    "ios": frozenset(),
    "miniapp": frozenset(),
    "desktop": frozenset(),
    "iot": frozenset(),
}

PLATFORM_CLAIM: dict[str, dict[str, str]] = {
    "web": {
        "status": "VERIFIED",
        "evidence": "V16-002 real Chromium interception/egress tests",
    },
    "android": {
        "status": "AVAILABLE",
        "evidence": "Appium local smoke only; real-device verification pending",
    },
    "ios": {"status": "BLOCKED", "evidence": "DeviceBroker IOS_ENABLED=false"},
    "miniapp": {"status": "BLOCKED", "evidence": "no real WeChat container runner"},
    "desktop": {"status": "BLOCKED", "evidence": "no desktop adapter/runner"},
    "iot": {"status": "BLOCKED", "evidence": "no IoT adapter/runner"},
}


class PlatformSupportError(ValueError):
    code = "PLATFORM_ACTION_UNSUPPORTED"


def assert_actions_supported(platform: str, actions: Iterable[str]) -> None:
    platform_id = str(platform or "").strip().lower()
    if platform_id not in ALL_PLATFORMS:
        raise PlatformSupportError(f"未知平台: {platform!r}")
    supported = PLATFORM_ACTIONS[platform_id]
    unsupported = sorted({str(action) for action in actions} - supported)
    if unsupported:
        raise PlatformSupportError(
            f"平台 {platform_id} 未支持动作: {unsupported}"
        )


def platform_claim(platform: str) -> dict[str, Any]:
    platform_id = str(platform or "").strip().lower()
    if platform_id not in PLATFORM_CLAIM:
        raise PlatformSupportError(f"未知平台: {platform!r}")
    claim: dict[str, Any] = dict(PLATFORM_CLAIM[platform_id])
    claim["platform"] = platform_id
    claim["ga_supported"] = platform_id in GA_SUPPORTED
    return claim


def ga_matrix() -> list[dict[str, Any]]:
    return [platform_claim(platform) for platform in sorted(ALL_PLATFORMS)]


__all__ = [
    "ALL_PLATFORMS",
    "BLOCKED_PLATFORMS",
    "GA_SUPPORTED",
    "PLATFORM_ACTIONS",
    "PLATFORM_CLAIM",
    "PlatformSupportError",
    "assert_actions_supported",
    "ga_matrix",
    "platform_claim",
]
