"""V16-007：Workflow 冻结快照服务（content-addressed + 克隆）。

- ``ensure_snapshot(db, workflow)``：按 workflow 内容生成/复用不可变快照；
- ``snapshot_from_graph(...)``：为 graph_override / 克隆生成新快照；
- ``clone_snapshot(...)``：完整复制 DAG（edges/depends_on/assertions/outputs 全部保留），
  可按实验设计移除节点（移除后重写依赖与边，并重新校验无悬挂/环路）；
- ``snapshot_graph(snapshot)``：返回快照 graph 的深拷贝（调用方不得修改快照本身）。
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.workflow import WorkflowDefinition, WorkflowSnapshot
from app.aiqe.security.target_policy import resolve_execution_policy
from app.aiqe.services.workflow_validator import (
    WorkflowValidationError,
    validate_workflow,
)

REGISTERED_DRIVERS = frozenset(
    {
        "http",
        "playwright",
        "db",
        "event",
        "mobile",
        "miniapp",
        "device",
        "external_e2e",
        "appium",
    }
)


class SnapshotError(ValueError):
    pass


def canonical_json(graph: Mapping[str, Any]) -> str:
    return json.dumps(dict(graph), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def checksum_of(graph: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(graph).encode("utf-8")).hexdigest()


def validate_graph(graph: Mapping[str, Any]) -> None:
    try:
        validate_workflow(dict(graph), registered_drivers=set(REGISTERED_DRIVERS))
    except WorkflowValidationError as exc:
        raise SnapshotError(f"Workflow 校验失败: {exc}") from exc


def _driver_manifest_hash(db: Session) -> str:
    from app.aiqe.models.capability import NodeCapabilityManifest

    rows = list(db.scalars(select(NodeCapabilityManifest)))
    payload = sorted(
        f"{row.driver_key or ''}:{row.driver_version or ''}:{row.runner_version or ''}"
        for row in rows
    )
    return hashlib.sha256("\n".join(payload).encode("utf-8")).hexdigest()


def _policy_binding(db: Session, project_id: int) -> tuple[str | None, int, str]:
    policy = resolve_execution_policy(db, project_id=project_id)
    return policy.policy_id, int(policy.version or 0), policy.policy_hash


def _registry_version(db: Session, project_id: int) -> str:
    from app.aiqe.models.query_registry import RegisteredQuery

    rows = list(
        db.scalars(
            select(RegisteredQuery).where(RegisteredQuery.project_id == int(project_id))
        )
    )
    if not rows:
        return ""
    digest = hashlib.sha256(
        "\n".join(sorted(f"{row.query_key}:{row.version}:{row.statement_hash}" for row in rows)).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"sha256:{digest}"


def _create_snapshot(
    db: Session,
    *,
    project_id: int,
    graph: Mapping[str, Any],
    workflow_id: str | None,
    workflow_version: int,
    execution_kind: str = "NORMAL",
    parent_snapshot_id: str | None = None,
    clone_diff: Mapping[str, Any] | None = None,
    created_by: int | None = None,
) -> WorkflowSnapshot:
    validate_graph(graph)
    project = int(project_id)
    policy_id, policy_version, policy_hash = _policy_binding(db, project)
    snapshot = WorkflowSnapshot(
        project_id=project,
        workflow_id=workflow_id,
        workflow_version=int(workflow_version),
        schema_version=str(graph.get("schema_version") or "1.0"),
        canonical_json=copy.deepcopy(dict(graph)),
        checksum_sha256=checksum_of(graph),
        parent_snapshot_id=parent_snapshot_id,
        clone_diff_json=dict(clone_diff) if clone_diff else None,
        execution_kind=str(execution_kind),
        target_policy_id=policy_id,
        target_policy_version=policy_version,
        target_policy_hash=policy_hash,
        query_registry_version=_registry_version(db, project),
        driver_manifest_hash=_driver_manifest_hash(db),
        created_by=created_by,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def ensure_snapshot(
    db: Session,
    workflow: WorkflowDefinition,
    *,
    execution_kind: str = "NORMAL",
    created_by: int | None = None,
) -> WorkflowSnapshot:
    """按内容取快照；已存在则复用（不可变、content-addressed）。"""
    graph = dict(workflow.graph_json or {})
    checksum = checksum_of(graph)
    existing = db.scalar(
        select(WorkflowSnapshot).where(
            WorkflowSnapshot.project_id == int(workflow.project_id),
            WorkflowSnapshot.workflow_id == str(workflow.id),
            WorkflowSnapshot.checksum_sha256 == checksum,
            WorkflowSnapshot.execution_kind == str(execution_kind),
        )
    )
    if existing is not None:
        return existing
    return _create_snapshot(
        db,
        project_id=int(workflow.project_id),
        graph=graph,
        workflow_id=str(workflow.id),
        workflow_version=int(workflow.version or 0),
        execution_kind=str(execution_kind),
        created_by=created_by,
    )


def snapshot_from_graph(
    db: Session,
    *,
    project_id: int,
    graph: Mapping[str, Any],
    workflow_id: str | None = None,
    workflow_version: int = 0,
    execution_kind: str = "NORMAL",
    parent_snapshot_id: str | None = None,
    created_by: int | None = None,
) -> WorkflowSnapshot:
    return _create_snapshot(
        db,
        project_id=int(project_id),
        graph=graph,
        workflow_id=workflow_id,
        workflow_version=int(workflow_version),
        execution_kind=str(execution_kind),
        parent_snapshot_id=parent_snapshot_id,
        created_by=created_by,
    )


def get_snapshot(db: Session, snapshot_id: str, *, project_id: int) -> WorkflowSnapshot:
    row = db.scalar(
        select(WorkflowSnapshot).where(
            WorkflowSnapshot.id == str(snapshot_id),
            WorkflowSnapshot.project_id == int(project_id),
        )
    )
    if row is None:
        raise SnapshotError(f"Snapshot 不存在或不属于当前项目: {snapshot_id}")
    return row


def snapshot_graph(snapshot: WorkflowSnapshot) -> dict[str, Any]:
    return copy.deepcopy(dict(snapshot.canonical_json or {}))


def clone_graph_with_diff(
    graph: Mapping[str, Any],
    *,
    remove_node_keys: Iterable[str] = (),
    remove_reasons: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """完整复制 DAG 并返回 clone diff（满足 §V16-007.6）。"""
    clone = copy.deepcopy(dict(graph))
    removed = {str(key) for key in remove_node_keys if str(key)}
    diff: dict[str, Any] = {
        "removed_nodes": [],
        "rewired_dependencies": [],
        "removed_edges": [],
    }
    if removed:
        reasons = dict(remove_reasons or {})
        for node in graph.get("nodes") or []:
            key = str(node.get("key"))
            if key in removed:
                diff["removed_nodes"].append(
                    {"key": key, "reason": reasons.get(key, "excluded_by_scope")}
                )
        clone["nodes"] = [
            node for node in clone.get("nodes") or [] if str(node.get("key")) not in removed
        ]
        for node in clone["nodes"]:
            original = [str(dep) for dep in (node.get("depends_on") or [])]
            kept = [dep for dep in original if dep not in removed]
            if kept != original:
                diff["rewired_dependencies"].append(
                    {
                        "node": str(node.get("key")),
                        "from": original,
                        "to": kept,
                    }
                )
            node["depends_on"] = kept
        kept_edges = []
        for edge in clone.get("edges") or []:
            if str(edge.get("from")) in removed or str(edge.get("to")) in removed:
                diff["removed_edges"].append(dict(edge))
                continue
            kept_edges.append(edge)
        clone["edges"] = kept_edges
    validate_graph(clone)
    return clone, diff


def clone_graph(
    graph: Mapping[str, Any],
    *,
    remove_node_keys: Iterable[str] = (),
) -> dict[str, Any]:
    """完整复制 DAG；可选移除节点并重写依赖/边（不硬编码 depends_on=[]）。"""
    clone, _diff = clone_graph_with_diff(graph, remove_node_keys=remove_node_keys)
    return clone


def clone_snapshot(
    db: Session,
    snapshot: WorkflowSnapshot,
    *,
    execution_kind: str,
    remove_node_keys: Iterable[str] = (),
    remove_reasons: Mapping[str, str] | None = None,
    created_by: int | None = None,
) -> WorkflowSnapshot:
    graph, diff = clone_graph_with_diff(
        snapshot.canonical_json or {},
        remove_node_keys=remove_node_keys,
        remove_reasons=remove_reasons,
    )
    if not remove_node_keys and checksum_of(graph) == snapshot.checksum_sha256:
        return snapshot
    return _create_snapshot(
        db,
        project_id=int(snapshot.project_id),
        graph=graph,
        workflow_id=snapshot.workflow_id,
        workflow_version=int(snapshot.workflow_version or 0),
        execution_kind=str(execution_kind),
        parent_snapshot_id=snapshot.id,
        clone_diff=diff,
        created_by=created_by,
    )


__all__ = [
    "REGISTERED_DRIVERS",
    "SnapshotError",
    "canonical_json",
    "checksum_of",
    "clone_graph",
    "clone_graph_with_diff",
    "clone_snapshot",
    "ensure_snapshot",
    "get_snapshot",
    "snapshot_from_graph",
    "snapshot_graph",
    "validate_graph",
]
