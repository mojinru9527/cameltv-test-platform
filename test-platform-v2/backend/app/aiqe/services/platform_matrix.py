"""batch-339：节点能力 × 平台矩阵（真实数据来自 `node_capability_manifests`）。

Console "平台矩阵"页只读聚合：
- platforms：所有节点自描述的平台并集；
- capabilities：所有节点能力并集；
- rows[].cells[platform]：命中该平台的可用节点（available=True）与 evidence；
- 无节点的平台/能力不出现在矩阵中（不造 mock）。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.capability import NodeCapabilityManifest


def _node_out(row: NodeCapabilityManifest) -> dict[str, Any]:
    return {
        "node_id": row.node_id,
        "driver_key": row.driver_key,
        "driver_version": row.driver_version,
        "platforms": list(row.platforms_json or []),
        "capabilities": list(row.capabilities_json or []),
        "available": bool(row.available),
        "last_evidence_ref": row.last_evidence_ref,
        "last_heartbeat_at": row.last_heartbeat_at,
    }


def build_platform_matrix(db: Session) -> dict[str, Any]:
    nodes = list(db.scalars(select(NodeCapabilityManifest).order_by(NodeCapabilityManifest.node_id)))
    platforms = sorted({platform for node in nodes for platform in (node.platforms_json or [])})
    capabilities = sorted(
        {capability for node in nodes for capability in (node.capabilities_json or [])}
    )

    rows: list[dict[str, Any]] = []
    for capability in capabilities:
        cells: dict[str, dict[str, Any]] = {}
        for platform in platforms:
            matched = [
                node
                for node in nodes
                if node.available
                and capability in (node.capabilities_json or [])
                and platform in (node.platforms_json or [])
            ]
            cells[platform] = {
                "available": bool(matched),
                "node_count": len(matched),
                "nodes": [node.node_id for node in matched],
            }
        rows.append({"capability": capability, "cells": cells})

    return {
        "platforms": platforms,
        "capabilities": capabilities,
        "rows": rows,
        "nodes": [_node_out(node) for node in nodes],
        "available_nodes": sum(1 for node in nodes if node.available),
    }
