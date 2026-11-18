"""AUD-020：多端平台绑定 / 按平台能力状态 / 多端 Preflight 验收测试。

对应 v1.5 §03 AUD-020「验收」：
- REGISTERED/AVAILABLE/VERIFIED 必须按真实节点能力区分；
- 只有真机/官方工具真实运行记录才能标 VERIFIED；
- 没有设备时 Run Preflight BLOCKED，不得 Mock 成 PASS；
- 聚合视图不能隐藏某一端未验证（PC PASS 不能代替 Mobile PASS）。
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.aiqe.models.contract import AiqeTestCase
from app.aiqe.services import capability_registry
from app.aiqe.services.platform_binding_service import (
    PLATFORMS,
    REAL_DEVICE_PLATFORMS,
    PlatformBindingError,
    create_binding,
    list_bindings,
    platform_matrix,
    preflight_platform,
    resolve_platform_status,
)


def _manifest(db, node_id, *, capabilities, platforms=(), evidence_ref="", verified=False):
    row = capability_registry.register_manifest(
        db,
        node_id=node_id,
        capabilities=capabilities,
        platforms=platforms,
        evidence_ref=evidence_ref,
        now=datetime.now(UTC),
    )
    if verified:
        capability_registry.mark_verified(db, node_id, platforms=platforms, evidence_ref="cap-1")
    return row


def test_platform_status_matrix():
    assert len(PLATFORMS) == 9
    assert REAL_DEVICE_PLATFORMS == {
        "native_android",
        "native_ios",
        "miniapp_wechat",
        "desktop_windows",
        "desktop_macos",
        "hardware_iot",
    }


def test_no_node_means_unavailable(db_session):
    status = resolve_platform_status(db_session, "native_ios")
    assert status.capability_status == "UNAVAILABLE"
    assert status.real_device is True
    assert status.node_ids == ()


def test_registered_available_verified_are_distinct(db_session):
    _manifest(db_session, "node-x", capabilities=["device.android"], platforms=["android"])
    assert resolve_platform_status(db_session, "native_android").capability_status == "REGISTERED"

    _manifest(
        db_session, "node-x", capabilities=["device.android"], platforms=["android"], evidence_ref="ev-1"
    )
    assert resolve_platform_status(db_session, "native_android").capability_status == "AVAILABLE"

    _manifest(
        db_session,
        "node-x",
        capabilities=["device.android"],
        platforms=["android"],
        evidence_ref="ev-1",
        verified=True,
    )
    status = resolve_platform_status(db_session, "native_android")
    assert status.capability_status == "VERIFIED"
    assert status.verified is True


def test_unknown_platform_rejected(db_session):
    with pytest.raises(PlatformBindingError):
        resolve_platform_status(db_session, "smart_fridge")


def test_binding_status_cannot_be_self_reported(db_session):
    case = AiqeTestCase(project_id=1, case_id="TC-PLAT-1", title="跨端登录")
    db_session.add(case)
    db_session.commit()

    binding = create_binding(
        db_session,
        project_id=1,
        target_type="CASE",
        target_id="TC-PLAT-1",
        platform_id="native_ios",
        os_version="iOS 18",
        device_model="iPhone 15",
        driver_name="appium",
        driver_version="2.x",
    )
    # 没有真机节点 → UNAVAILABLE，即使调用方传了 driver 信息
    assert binding.capability_status == "UNAVAILABLE"
    assert binding.target_type == "CASE"

    _manifest(db_session, "node-ios", capabilities=["device.ios"], platforms=["ios"])
    updated = create_binding(
        db_session,
        project_id=1,
        target_type="CASE",
        target_id="TC-PLAT-1",
        platform_id="native_ios",
        device_model="iPhone 15",
    )
    assert updated.id == binding.id  # 同一 target+platform 复用
    assert updated.capability_status == "REGISTERED"


def test_binding_requires_existing_target(db_session):
    with pytest.raises(PlatformBindingError):
        create_binding(
            db_session,
            project_id=1,
            target_type="CASE",
            target_id="TC-MISSING",
            platform_id="web_desktop",
        )
    with pytest.raises(PlatformBindingError):
        create_binding(
            db_session,
            project_id=1,
            target_type="NONSENSE",
            target_id="x",
            platform_id="web_desktop",
        )


def test_preflight_blocks_missing_mobile_while_web_ready(db_session):
    _manifest(
        db_session,
        "node-web",
        capabilities=["browser.chromium"],
        platforms=["linux"],
        evidence_ref="ev-web",
    )
    result = preflight_platform(db_session, ["web_desktop", "native_ios"])
    assert result["allowed"] is False
    assert result["status"] == "BLOCKED"
    blocked = {item["platform_id"]: item["code"] for item in result["blockers"]}
    assert blocked["native_ios"] == "PLATFORM_UNAVAILABLE"
    assert "web_desktop" not in blocked


def test_preflight_requires_verified_for_real_device(db_session):
    _manifest(
        db_session,
        "node-ios",
        capabilities=["device.ios"],
        platforms=["ios"],
        evidence_ref="ev-1",
    )
    result = preflight_platform(db_session, ["native_ios"])
    assert result["allowed"] is False
    assert result["blockers"][0]["code"] == "PLATFORM_NOT_VERIFIED"

    _manifest(
        db_session,
        "node-ios",
        capabilities=["device.ios"],
        platforms=["ios"],
        evidence_ref="ev-1",
        verified=True,
    )
    result = preflight_platform(db_session, ["native_ios"])
    assert result["allowed"] is True


def test_platform_matrix_never_hides_unverified(db_session):
    _manifest(
        db_session,
        "node-web",
        capabilities=["browser.chromium"],
        platforms=["linux"],
        evidence_ref="ev-web",
    )
    _manifest(db_session, "node-android", capabilities=["device.android"], platforms=["android"])
    case = AiqeTestCase(project_id=1, case_id="TC-PLAT-2", title="跨端入口")
    db_session.add(case)
    db_session.commit()
    create_binding(
        db_session, project_id=1, target_type="CASE", target_id="TC-PLAT-2", platform_id="web_desktop"
    )
    create_binding(
        db_session, project_id=1, target_type="CASE", target_id="TC-PLAT-2", platform_id="native_android"
    )
    matrix = platform_matrix(db_session, project_id=1)
    statuses = {item["platform_id"]: item["capability_status"] for item in matrix["platforms"]}
    assert statuses["web_desktop"] == "AVAILABLE"
    assert statuses["native_android"] == "REGISTERED"
    assert "native_android" in matrix["unverified_platforms"]
    assert matrix["complete"] is False
    assert len(list_bindings(db_session, project_id=1)) == 2
