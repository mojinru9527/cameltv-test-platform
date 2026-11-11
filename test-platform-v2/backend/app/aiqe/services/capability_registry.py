"""M2 / TA-015：Driver Registry + Capability（13 号 §4.22 / §19 TA-015）。

- 节点自描述能力 + 实测 evidence（last_evidence_ref 为空则 available=False）；
- `select_nodes(required)` 只返回覆盖全部要求能力的节点（缺 WebKit 的节点不会接 WebKit 任务）；
- `known_capabilities()` 供 Workflow Validator 的 registered_capabilities 使用。
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

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
    }
)


class CapabilityError(ValueError):
    pass


def known_capabilities() -> frozenset[str]:
    return STANDARD_CAPABILITIES


def _normalize(values: Iterable[str]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def get_manifest(db: Session, node_id: str) -> NodeCapabilityManifest | None:
    return db.scalar(
        select(NodeCapabilityManifest)
        .where(NodeCapabilityManifest.node_id == node_id)
        .with_for_update()
    )


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
) -> NodeCapabilityManifest:
    if not node_id or not str(node_id).strip():
        raise CapabilityError("node_id 不能为空")
    caps = _normalize(capabilities)
    if not caps:
        raise CapabilityError("capabilities 不能为空")
    if max_parallel_sessions < 1:
        raise CapabilityError("max_parallel_sessions 必须 >= 1")

    row = get_manifest(db, str(node_id).strip())
    if row is None:
        row = NodeCapabilityManifest(node_id=str(node_id).strip())
        db.add(row)
    row.driver_key = driver_key
    row.driver_version = driver_version
    row.capabilities_json = caps
    row.platforms_json = _normalize(platforms)
    row.max_parallel_sessions = int(max_parallel_sessions)
    row.artifact_types_json = _normalize(artifact_types)
    row.last_evidence_ref = evidence_ref
    row.available = bool(evidence_ref) and bool(caps)
    row.last_heartbeat_at = heartbeat_at or datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def record_evidence(db: Session, node_id: str, evidence_ref: str) -> NodeCapabilityManifest:
    """实测 evidence 回填；只有拿到 evidence 才允许 available=True。"""
    if not evidence_ref:
        raise CapabilityError("evidence_ref 不能为空")
    row = get_manifest(db, node_id)
    if row is None:
        raise CapabilityError(f"节点不存在: {node_id}")
    row.last_evidence_ref = evidence_ref
    row.available = bool(row.capabilities_json)
    row.updated_at = datetime.now(UTC)
    db.flush()
    return row


def supports(db: Session, node_id: str, capability: str) -> bool:
    row = get_manifest(db, node_id)
    return bool(row and row.available and capability in (row.capabilities_json or []))


def select_nodes(db: Session, required: Iterable[str]) -> list[str]:
    required_set = set(_normalize(required))
    if not required_set:
        return [
            row.node_id
            for row in db.scalars(
                select(NodeCapabilityManifest).where(NodeCapabilityManifest.available.is_(True))
            )
        ]
    rows = db.scalars(
        select(NodeCapabilityManifest).where(NodeCapabilityManifest.available.is_(True))
    )
    return sorted(
        row.node_id
        for row in rows
        if required_set.issubset(set(row.capabilities_json or []))
    )
