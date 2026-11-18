"""AUD-020：多端平台绑定与按平台能力状态（服务端计算，禁止自报）。

- 平台能力状态来自 Capability Registry（REGISTERED/AVAILABLE/VERIFIED/DEGRADED/
  UNAVAILABLE/REVOKED），客户端只能提供绑定元数据，不能声明 VERIFIED；
- 每个平台独立记录 OS/浏览器或 App 版本/设备型号/Driver 版本/节点；
- 没有真机/官方工具时该平台 Preflight BLOCKED，聚合视图不得隐藏某一端未验证。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.capability import NodeCapabilityManifest
from app.aiqe.models.contract import AcceptanceCriterion, AiqeTestCase
from app.aiqe.models.platform_binding import PlatformBinding
from app.aiqe.services import capability_registry

PLATFORMS: tuple[str, ...] = (
    "web_desktop",
    "mobile_web_android",
    "mobile_web_ios",
    "native_android",
    "native_ios",
    "miniapp_wechat",
    "desktop_windows",
    "desktop_macos",
    "hardware_iot",
)
#: 平台 → 必需能力（与 capability_registry.STANDARD_CAPABILITIES 对应）。
PLATFORM_REQUIRED_CAPABILITY: dict[str, str] = {
    "web_desktop": "browser.chromium",
    "mobile_web_android": "browser.chromium",
    "mobile_web_ios": "browser.webkit",
    "native_android": "device.android",
    "native_ios": "device.ios",
    "miniapp_wechat": "miniapp.wechat",
    "desktop_windows": "desktop.app",
    "desktop_macos": "desktop.app",
    "hardware_iot": "hardware.iot",
}
#: 真机/官方工具平台：只有 VERIFIED 才允许作为验收证据。
REAL_DEVICE_PLATFORMS: frozenset[str] = frozenset(
    {"native_android", "native_ios", "miniapp_wechat", "desktop_windows", "desktop_macos", "hardware_iot"}
)
TARGET_TYPES: frozenset[str] = frozenset({"AC", "CASE"})


class PlatformBindingError(ValueError):
    pass


@dataclass(frozen=True)
class PlatformStatus:
    platform_id: str
    capability_status: str
    required_capability: str
    node_ids: tuple[str, ...]
    real_device: bool

    @property
    def verified(self) -> bool:
        return self.capability_status == capability_registry.CapabilityStatus.VERIFIED.value

    def payload(self) -> dict[str, Any]:
        return {
            "platform_id": self.platform_id,
            "capability_status": self.capability_status,
            "required_capability": self.required_capability,
            "node_ids": list(self.node_ids),
            "real_device": self.real_device,
            "verified": self.verified,
        }


def resolve_platform_status(
    db: Session, platform_id: str, *, now=None
) -> PlatformStatus:
    """按 Capability Registry 计算平台状态（不信任客户端声明）。"""
    platform = str(platform_id or "").strip()
    if platform not in PLATFORMS:
        raise PlatformBindingError(f"未知平台: {platform_id!r}")
    capability = PLATFORM_REQUIRED_CAPABILITY[platform]
    rows = list(
        db.scalars(
            select(NodeCapabilityManifest).where(
                NodeCapabilityManifest.capabilities_json.isnot(None)
            )
        )
    )
    matching = [
        row for row in rows if capability in (row.capabilities_json or [])
    ]
    if not matching:
        return PlatformStatus(
            platform_id=platform,
            capability_status=capability_registry.CapabilityStatus.UNAVAILABLE.value,
            required_capability=capability,
            node_ids=(),
            real_device=platform in REAL_DEVICE_PLATFORMS,
        )
    statuses = {
        row.node_id: capability_registry.compute_effective_status(row, now=now)
        for row in matching
    }
    verified_nodes = tuple(
        node_id
        for node_id, status in statuses.items()
        if status == capability_registry.CapabilityStatus.VERIFIED.value
    )
    if verified_nodes:
        final = capability_registry.CapabilityStatus.VERIFIED.value
    elif any(
        status == capability_registry.CapabilityStatus.AVAILABLE.value
        for status in statuses.values()
    ):
        final = capability_registry.CapabilityStatus.AVAILABLE.value
    elif any(
        status == capability_registry.CapabilityStatus.DEGRADED.value
        for status in statuses.values()
    ):
        final = capability_registry.CapabilityStatus.DEGRADED.value
    elif any(
        status == capability_registry.CapabilityStatus.REVOKED.value
        for status in statuses.values()
    ):
        final = capability_registry.CapabilityStatus.REVOKED.value
    else:
        final = capability_registry.CapabilityStatus.REGISTERED.value
    return PlatformStatus(
        platform_id=platform,
        capability_status=final,
        required_capability=capability,
        node_ids=tuple(sorted(statuses)),
        real_device=platform in REAL_DEVICE_PLATFORMS,
    )


def _assert_target(db: Session, project_id: int, target_type: str, target_id: str) -> None:
    kind = str(target_type or "").upper()
    if kind not in TARGET_TYPES:
        raise PlatformBindingError("target_type 只能是 AC/CASE")
    if kind == "AC":
        ac_row = db.scalar(
            select(AcceptanceCriterion).where(AcceptanceCriterion.ac_id == str(target_id))
        )
        if ac_row is None:
            raise PlatformBindingError(f"AC 不存在: {target_id}")
    else:
        case_row = db.scalar(
            select(AiqeTestCase).where(
                AiqeTestCase.project_id == int(project_id),
                AiqeTestCase.case_id == str(target_id),
            )
        )
        if case_row is None:
            raise PlatformBindingError(f"Case 不存在: {target_id}")


def create_binding(
    db: Session,
    *,
    project_id: int,
    target_type: str,
    target_id: str,
    platform_id: str,
    os_version: str = "",
    browser_or_app_version: str = "",
    device_model: str = "",
    driver_name: str = "",
    driver_version: str = "",
    node_id: str = "",
    test_profile: str = "",
    evidence_refs: list[str] | None = None,
    now=None,
) -> PlatformBinding:
    """创建/更新绑定；capability_status 由服务端计算。"""
    _assert_target(db, project_id, target_type, target_id)
    status = resolve_platform_status(db, platform_id, now=now)
    existing = db.scalar(
        select(PlatformBinding).where(
            PlatformBinding.project_id == int(project_id),
            PlatformBinding.target_type == str(target_type).upper(),
            PlatformBinding.target_id == str(target_id),
            PlatformBinding.platform_id == status.platform_id,
        )
    )
    row = existing or PlatformBinding(
        project_id=int(project_id),
        target_type=str(target_type).upper(),
        target_id=str(target_id),
        platform_id=status.platform_id,
    )
    row.os_version = str(os_version or "")
    row.browser_or_app_version = str(browser_or_app_version or "")
    row.device_model = str(device_model or "")
    row.driver_name = str(driver_name or "")
    row.driver_version = str(driver_version or "")
    row.node_id = str(node_id or (status.node_ids[0] if status.node_ids else ""))
    row.test_profile = str(test_profile or "")
    row.evidence_refs_json = list(evidence_refs or [])
    # 客户端不能自报 VERIFIED：状态永远以服务端计算为准。
    row.capability_status = status.capability_status
    if existing is None:
        db.add(row)
    db.flush()
    return row


def list_bindings(
    db: Session, *, project_id: int, target_type: str | None = None, target_id: str | None = None
) -> list[PlatformBinding]:
    stmt = select(PlatformBinding).where(PlatformBinding.project_id == int(project_id))
    if target_type:
        stmt = stmt.where(PlatformBinding.target_type == str(target_type).upper())
    if target_id:
        stmt = stmt.where(PlatformBinding.target_id == str(target_id))
    return list(db.scalars(stmt.order_by(PlatformBinding.platform_id)))


def platform_matrix(db: Session, *, project_id: int, now=None) -> dict[str, Any]:
    """按平台聚合：状态、绑定数、未验证标记（不得隐藏某端未验证）。"""
    bindings = list_bindings(db, project_id=project_id)
    by_platform: dict[str, list[PlatformBinding]] = {}
    for binding in bindings:
        by_platform.setdefault(binding.platform_id, []).append(binding)
    platforms: list[dict[str, Any]] = []
    for platform in PLATFORMS:
        status = resolve_platform_status(db, platform, now=now)
        rows = by_platform.get(platform, [])
        platforms.append(
            {
                **status.payload(),
                "bindings": len(rows),
                "targets": sorted({f"{row.target_type}:{row.target_id}" for row in rows}),
                "evidence_refs": sorted(
                    {ref for row in rows for ref in (row.evidence_refs_json or [])}
                ),
            }
        )
    verified = [item["platform_id"] for item in platforms if item["verified"]]
    unverified = [item["platform_id"] for item in platforms if not item["verified"]]
    return {
        "project_id": int(project_id),
        "platforms": platforms,
        "verified_platforms": verified,
        "unverified_platforms": unverified,
        "complete": all(
            item["verified"]
            for item in platforms
            if item["bindings"] > 0
        ),
    }


def preflight_platform(
    db: Session, platforms: list[str], *, require_verified_for_real_devices: bool = True, now=None
) -> dict[str, Any]:
    """多端 Preflight：缺设备/未验证 → BLOCKED，并逐平台给出原因。"""
    blockers: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    for platform in platforms:
        try:
            status = resolve_platform_status(db, platform, now=now)
        except PlatformBindingError as exc:
            blockers.append({"code": "UNKNOWN_PLATFORM", "platform_id": platform, "message": str(exc)})
            continue
        checked.append(status.payload())
        needs_verified = require_verified_for_real_devices and status.real_device
        if status.capability_status == capability_registry.CapabilityStatus.UNAVAILABLE.value:
            blockers.append(
                {
                    "code": "PLATFORM_UNAVAILABLE",
                    "platform_id": platform,
                    "message": f"没有可用节点提供能力 {status.required_capability}",
                }
            )
        elif needs_verified and not status.verified:
            blockers.append(
                {
                    "code": "PLATFORM_NOT_VERIFIED",
                    "platform_id": platform,
                    "message": f"真机/官方工具平台必须 VERIFIED，当前 {status.capability_status}",
                }
            )
    return {
        "allowed": not blockers,
        "status": "READY" if not blockers else "BLOCKED",
        "platforms": checked,
        "blockers": blockers,
    }


__all__ = [
    "PLATFORMS",
    "PLATFORM_REQUIRED_CAPABILITY",
    "REAL_DEVICE_PLATFORMS",
    "PlatformBindingError",
    "PlatformStatus",
    "create_binding",
    "list_bindings",
    "platform_matrix",
    "preflight_platform",
    "resolve_platform_status",
]
