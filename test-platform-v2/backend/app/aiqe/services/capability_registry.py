"""M2 / TA-015 + AUD-005：Driver Capability Registry（6 态 + VERIFIED 证据链）。

v1.5 §01 AUD-005 不变量：

- 声明能力 ≠ 真实能力：``REGISTERED``（只有 Manifest）与 ``AVAILABLE``（在线且有心跳/证据）
  与 ``VERIFIED``（在该版本/OS/浏览器/设备配置下真实跑过验收）必须可区分；
- Runner 失联/依赖异常 → ``DEGRADED``/``UNAVAILABLE``，管理员禁用 → ``REVOKED``；
- **软件更新后 VERIFIED 必须降级**（``invalidate_verification``），要重新验收；
- ``select_nodes`` 只返回状态允许且覆盖全部所需能力的节点；缺能力时由 Preflight 在
  Launch 前 BLOCKED，而不是执行期才发现。
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.capability import NodeCapabilityManifest

STANDARD_CAPABILITIES: frozenset[str] = frozenset(
    {
        "browser.chromium",
        "browser.firefox",
        "browser.webkit",
        "browser.trace",
        "browser.a11y",
        "browser.video",
        "api.http",
        "db.readonly",
        "device.android",
        "device.ios",
        "mobile.app",
        "desktop.app",
        "miniapp.wechat",
        "external.e2e",
        "hardware.iot",
    }
)

DEFAULT_HEARTBEAT_TTL_SECONDS = 180


class CapabilityStatus(StrEnum):
    REGISTERED = "REGISTERED"
    AVAILABLE = "AVAILABLE"
    VERIFIED = "VERIFIED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    REVOKED = "REVOKED"


#: 可用于派发的状态（VERIFIED 高于 AVAILABLE）。
SCHEDULABLE_STATUSES: frozenset[str] = frozenset(
    {CapabilityStatus.AVAILABLE.value, CapabilityStatus.VERIFIED.value}
)


class CapabilityError(ValueError):
    pass


def known_capabilities() -> frozenset[str]:
    return STANDARD_CAPABILITIES


def _normalize(values: Iterable[str]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _aware(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def is_schedulable(status: str | None) -> bool:
    return str(status or "") in SCHEDULABLE_STATUSES


def get_manifest(db: Session, node_id: str) -> NodeCapabilityManifest | None:
    return db.scalar(
        select(NodeCapabilityManifest)
        .where(NodeCapabilityManifest.node_id == node_id)
        .with_for_update()
    )


def compute_effective_status(
    row: NodeCapabilityManifest,
    *,
    now: datetime | None = None,
    heartbeat_ttl_seconds: int = DEFAULT_HEARTBEAT_TTL_SECONDS,
) -> str:
    """结合心跳新鲜度计算**当前**状态（不改库，供预检/展示）。"""
    status = str(row.capability_status or CapabilityStatus.REGISTERED.value)
    if status == CapabilityStatus.REVOKED.value:
        return status
    moment = now or datetime.now(UTC)
    heartbeat = _aware(row.last_heartbeat_at)
    if heartbeat is None:
        return CapabilityStatus.UNAVAILABLE.value
    age = moment - heartbeat
    if age > timedelta(seconds=max(1, int(heartbeat_ttl_seconds))):
        return CapabilityStatus.UNAVAILABLE.value
    if status == CapabilityStatus.DEGRADED.value:
        return status
    if not row.capabilities_json:
        return CapabilityStatus.REGISTERED.value
    if not row.last_evidence_ref:
        return CapabilityStatus.REGISTERED.value
    if status == CapabilityStatus.VERIFIED.value and row.verified_at is not None:
        return CapabilityStatus.VERIFIED.value
    return CapabilityStatus.AVAILABLE.value


def _apply_status(
    row: NodeCapabilityManifest,
    status: CapabilityStatus,
    *,
    reason: str = "",
    now: datetime | None = None,
) -> None:
    row.capability_status = status.value
    row.status_reason = reason[:255]
    row.available = status.value in SCHEDULABLE_STATUSES
    row.updated_at = now or datetime.now(UTC)


def register_manifest(
    db: Session,
    *,
    node_id: str,
    driver_key: str = "",
    driver_version: str = "",
    capabilities: Iterable[str] = (),
    platforms: Iterable[str] = (),
    max_parallel_sessions: int = 1,
    artifact_types: Iterable[str] = (),
    evidence_ref: str = "",
    heartbeat_at: datetime | None = None,
    runner_version: str = "",
    manifest_version: str = "",
    signature: str = "",
    now: datetime | None = None,
) -> NodeCapabilityManifest:
    if not node_id or not str(node_id).strip():
        raise CapabilityError("node_id 不能为空")
    caps = _normalize(capabilities)
    if not caps:
        raise CapabilityError("capabilities 不能为空")
    if max_parallel_sessions < 1:
        raise CapabilityError("max_parallel_sessions 必须 >= 1")

    moment = now or datetime.now(UTC)
    row = get_manifest(db, str(node_id).strip())
    if row is None:
        row = NodeCapabilityManifest(node_id=str(node_id).strip())
        db.add(row)
    previous_driver_version = str(row.driver_version or "")
    previous_runner_version = str(row.runner_version or "")
    row.driver_key = driver_key
    row.driver_version = driver_version
    row.runner_version = runner_version
    row.manifest_version = manifest_version
    row.manifest_signature = signature
    row.capabilities_json = caps
    row.platforms_json = _normalize(platforms)
    row.max_parallel_sessions = int(max_parallel_sessions)
    row.artifact_types_json = _normalize(artifact_types)
    row.last_evidence_ref = evidence_ref
    row.last_heartbeat_at = heartbeat_at or moment

    invalidated = bool(
        row.verified_at is not None
        and (
            (driver_version and driver_version != previous_driver_version)
            or (runner_version and runner_version != previous_runner_version)
        )
    )
    if invalidated:
        row.verified_at = None
        row.verified_platforms_json = []
        _apply_status(
            row,
            CapabilityStatus.AVAILABLE if evidence_ref else CapabilityStatus.REGISTERED,
            reason="SOFTWARE_UPDATED_REVERIFY_REQUIRED",
            now=moment,
        )
    elif bool(evidence_ref) and bool(caps):
        _apply_status(row, CapabilityStatus.AVAILABLE, now=moment)
    else:
        _apply_status(row, CapabilityStatus.REGISTERED, now=moment)
    db.flush()
    return row


def heartbeat(
    db: Session, node_id: str, *, now: datetime | None = None
) -> NodeCapabilityManifest:
    """节点存活心跳：刷新 last_heartbeat_at，并恢复因心跳过期而降级的状态。

    - REVOKED 节点拒绝心跳（不得借心跳复活）；
    - DEGRADED 保持降级（依赖异常需重新验收/恢复后才可调度）；
    - VERIFIED 保持 VERIFIED，其余有 evidence 的恢复 AVAILABLE。
    """
    row = get_manifest(db, node_id)
    if row is None:
        raise LookupError(node_id)
    current = str(row.capability_status or CapabilityStatus.REGISTERED.value)
    if current == CapabilityStatus.REVOKED.value:
        raise CapabilityError("节点已 REVOKED，禁止心跳")
    moment = now or datetime.now(UTC)
    row.last_heartbeat_at = moment
    if current == CapabilityStatus.DEGRADED.value:
        status = CapabilityStatus.DEGRADED
    elif row.verified_at is not None and row.verified_platforms_json:
        status = CapabilityStatus.VERIFIED
    elif row.last_evidence_ref and row.capabilities_json:
        status = CapabilityStatus.AVAILABLE
    else:
        status = CapabilityStatus.REGISTERED
    _apply_status(row, status, reason="HEARTBEAT", now=moment)
    db.flush()
    return row


def record_evidence(db: Session, node_id: str, evidence_ref: str) -> NodeCapabilityManifest:
    """实测 evidence 回填；只有拿到 evidence 才允许 AVAILABLE。"""
    if not evidence_ref:
        raise CapabilityError("evidence_ref 不能为空")
    row = get_manifest(db, node_id)
    if row is None:
        raise CapabilityError(f"节点不存在: {node_id}")
    row.last_evidence_ref = evidence_ref
    if row.capability_status in {
        CapabilityStatus.REVOKED.value,
        CapabilityStatus.DEGRADED.value,
    }:
        db.flush()
        return row
    _apply_status(
        row,
        CapabilityStatus.AVAILABLE if row.capabilities_json else CapabilityStatus.REGISTERED,
    )
    db.flush()
    return row


def mark_verified(
    db: Session,
    node_id: str,
    *,
    platforms: Iterable[str],
    evidence_ref: str,
    now: datetime | None = None,
) -> NodeCapabilityManifest:
    """真实验收通过才允许 VERIFIED；必须给出实际跑过的平台与证据。"""
    verified = _normalize(platforms)
    if not verified:
        raise CapabilityError("VERIFIED 必须记录实际验收平台")
    if not str(evidence_ref or "").strip():
        raise CapabilityError("VERIFIED 必须提供证据引用")
    row = get_manifest(db, node_id)
    if row is None:
        raise CapabilityError(f"节点不存在: {node_id}")
    if row.capability_status == CapabilityStatus.REVOKED.value:
        raise CapabilityError("已 REVOKED 的节点不能直接 VERIFIED，需先恢复")
    moment = now or datetime.now(UTC)
    row.verified_platforms_json = verified
    row.last_evidence_ref = str(evidence_ref)
    row.verified_at = moment
    row.last_heartbeat_at = row.last_heartbeat_at or moment
    _apply_status(row, CapabilityStatus.VERIFIED, now=moment)
    db.flush()
    return row


def invalidate_verification(
    db: Session,
    *,
    node_ids: Iterable[str] | None = None,
    reason: str = "SOFTWARE_UPDATED_REVERIFY_REQUIRED",
    now: datetime | None = None,
) -> list[str]:
    """软件更新后降级 VERIFIED → AVAILABLE（v1.5 §01 AUD-005 第 4 条）。"""
    query = select(NodeCapabilityManifest)
    if node_ids is not None:
        query = query.where(NodeCapabilityManifest.node_id.in_(list(node_ids)))
    rows = list(db.scalars(query))
    affected: list[str] = []
    for row in rows:
        if row.capability_status != CapabilityStatus.VERIFIED.value:
            continue
        row.verified_at = None
        row.verified_platforms_json = []
        _apply_status(
            row,
            CapabilityStatus.AVAILABLE if row.last_evidence_ref else CapabilityStatus.REGISTERED,
            reason=reason,
            now=now,
        )
        affected.append(row.node_id)
    db.flush()
    return affected


def mark_degraded(db: Session, node_id: str, reason: str) -> NodeCapabilityManifest:
    row = get_manifest(db, node_id)
    if row is None:
        raise CapabilityError(f"节点不存在: {node_id}")
    _apply_status(row, CapabilityStatus.DEGRADED, reason=reason)
    db.flush()
    return row


def revoke(db: Session, node_id: str, reason: str) -> NodeCapabilityManifest:
    row = get_manifest(db, node_id)
    if row is None:
        raise CapabilityError(f"节点不存在: {node_id}")
    row.verified_at = None
    _apply_status(row, CapabilityStatus.REVOKED, reason=reason)
    db.flush()
    return row


def restore(db: Session, node_id: str, *, now: datetime | None = None) -> NodeCapabilityManifest:
    row = get_manifest(db, node_id)
    if row is None:
        raise CapabilityError(f"节点不存在: {node_id}")
    if row.capability_status != CapabilityStatus.REVOKED.value:
        return row
    _apply_status(
        row,
        CapabilityStatus.AVAILABLE if row.last_evidence_ref else CapabilityStatus.REGISTERED,
        reason="RESTORED",
        now=now,
    )
    db.flush()
    return row


def supports(db: Session, node_id: str, capability: str) -> bool:
    row = get_manifest(db, node_id)
    if row is None:
        return False
    status = compute_effective_status(row)
    return is_schedulable(status) and capability in (row.capabilities_json or [])


def select_nodes(
    db: Session,
    required: Iterable[str],
    *,
    allow_statuses: Iterable[str] = SCHEDULABLE_STATUSES,
    now: datetime | None = None,
) -> list[str]:
    """返回状态允许且覆盖全部所需能力的节点（按 node_id 排序）。"""
    required_set = set(_normalize(required))
    allowed = {str(status) for status in allow_statuses}
    rows = list(db.scalars(select(NodeCapabilityManifest)))
    selected: list[str] = []
    for row in rows:
        status = compute_effective_status(row, now=now)
        if status not in allowed:
            continue
        if required_set and not required_set.issubset(set(row.capabilities_json or [])):
            continue
        selected.append(row.node_id)
    return sorted(selected)


def effective_status(db: Session, node_id: str, *, now: datetime | None = None) -> str:
    row = get_manifest(db, node_id)
    if row is None:
        return CapabilityStatus.UNAVAILABLE.value
    return compute_effective_status(row, now=now)


def platform_matrix(db: Session, *, now: datetime | None = None) -> list[dict]:
    """按节点列出平台与状态（AUD-020 的聚合视图基础）。"""
    rows = list(db.scalars(select(NodeCapabilityManifest).order_by(NodeCapabilityManifest.node_id)))
    matrix: list[dict] = []
    for row in rows:
        status = compute_effective_status(row, now=now)
        matrix.append(
            {
                "node_id": row.node_id,
                "driver_key": row.driver_key,
                "driver_version": row.driver_version,
                "capabilities": list(row.capabilities_json or []),
                "platforms": list(row.platforms_json or []),
                "verified_platforms": list(row.verified_platforms_json or []),
                "capability_status": status,
                "available": is_schedulable(status),
                "status_reason": row.status_reason,
                "last_heartbeat_at": row.last_heartbeat_at.isoformat()
                if row.last_heartbeat_at
                else None,
                "verified_at": row.verified_at.isoformat() if row.verified_at else None,
            }
        )
    return matrix


__all__ = [
    "DEFAULT_HEARTBEAT_TTL_SECONDS",
    "SCHEDULABLE_STATUSES",
    "STANDARD_CAPABILITIES",
    "CapabilityError",
    "CapabilityStatus",
    "compute_effective_status",
    "effective_status",
    "get_manifest",
    "invalidate_verification",
    "is_schedulable",
    "known_capabilities",
    "mark_degraded",
    "mark_verified",
    "platform_matrix",
    "record_evidence",
    "register_manifest",
    "restore",
    "revoke",
    "select_nodes",
    "supports",
]
