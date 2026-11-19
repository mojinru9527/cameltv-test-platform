"""V16-016 验收：多端边界、动作粒度、设备租约与 GA 声明。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.aiqe.services.device_broker import (
    Device,
    DeviceBroker,
    DeviceBrokerError,
    NoDeviceAvailable,
    PlatformNotEnabled,
)
from app.aiqe.services.platform_support import (
    GA_SUPPORTED,
    PlatformSupportError,
    assert_actions_supported,
    ga_matrix,
    platform_claim,
)
from app.aiqe.services.preflight import preflight_graph


def test_ga_matrix_only_web_is_verified_and_ga():
    matrix = {row["platform"]: row for row in ga_matrix()}
    assert GA_SUPPORTED == {"web"}
    assert matrix["web"]["status"] == "VERIFIED"
    assert matrix["web"]["ga_supported"] is True
    for platform in ("ios", "miniapp", "desktop", "iot"):
        assert matrix[platform]["status"] == "BLOCKED"
        assert matrix[platform]["ga_supported"] is False
    assert matrix["android"]["status"] == "AVAILABLE"
    assert matrix["android"]["ga_supported"] is False


def test_platform_actions_supported_and_unsupported():
    assert_actions_supported("web", ["navigate", "click", "screenshot"])
    assert_actions_supported("android", ["install", "launch", "permission", "cleanup"])
    with pytest.raises(PlatformSupportError):
        assert_actions_supported("ios", ["click"])
    with pytest.raises(PlatformSupportError):
        assert_actions_supported("web", ["install"])
    with pytest.raises(PlatformSupportError):
        assert_actions_supported("unknown", ["click"])
    with pytest.raises(PlatformSupportError):
        platform_claim("unknown")


def test_preflight_blocks_unsupported_platform_actions(db_session):
    graph = {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "ios-click",
                "driver": "playwright",
                "platform": "ios",
                "actions": ["click"],
                "input": {"url": "https://app.test/x"},
            }
        ],
        "edges": [],
    }
    report = preflight_graph(db_session, graph, inprocess_enabled=True)
    assert any(issue.code == "PLATFORM_ACTION_UNSUPPORTED" for issue in report.issues)


def test_device_broker_lease_expiry_reaps_and_recovers():
    broker = DeviceBroker(
        [
            Device(
                device_id="android-1",
                platform="android",
                capabilities={"click", "screenshot"},
                lease_seconds=60,
            )
        ]
    )
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    device = broker.allocate("android", capabilities=("click",), now=t0)
    assert device.status == "busy"
    with pytest.raises(NoDeviceAvailable):
        broker.allocate("android", capabilities=("click",), now=t0 + timedelta(seconds=1))
    released = broker.reap_expired(now=t0 + timedelta(seconds=61))
    assert released == ["android-1"]
    assert broker.list_devices(platform="android")[0].status == "available"
    assert broker.health()["available"] == 1

    broker.mark_offline("android-1", reason="DISCONNECTED")
    with pytest.raises(NoDeviceAvailable):
        broker.allocate("android")
    broker.recover("android-1")
    assert broker.allocate("android").device_id == "android-1"


def test_device_broker_ios_disabled_and_release_rules():
    broker = DeviceBroker()
    with pytest.raises(PlatformNotEnabled):
        broker.register(Device(device_id="ios-1", platform="ios"))
    with pytest.raises(PlatformNotEnabled):
        broker.allocate("ios")
    with pytest.raises(DeviceBrokerError):
        broker.release("missing")
    android = Device(device_id="android-2", platform="android")
    broker.register(android)
    with pytest.raises(DeviceBrokerError):
        broker.release("android-2")  # 未占用不能 release
    broker.allocate("android")
    assert broker.release("android-2", reason="DONE").status == "available"


def test_platform_binding_records_environment_pool_runner(db_session):
    from app.aiqe.models.platform_binding import PlatformBinding

    row = PlatformBinding(
        project_id=1,
        target_type="AC",
        target_id="AC-1",
        platform_id="web",
        environment_id=3,
        device_pool="chromium-pool",
        runner_version="1.61.0",
    )
    db_session.add(row)
    db_session.flush()
    assert row.environment_id == 3
    assert row.device_pool == "chromium-pool"
    assert row.runner_version == "1.61.0"
