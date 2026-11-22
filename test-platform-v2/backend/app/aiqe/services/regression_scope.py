"""V16-008：Scope 计算与 Snapshot 持久化（服务端唯一事实源）。"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.regression_scope import (
    RULE_VERSION,
    RegressionScopeSnapshot,
    scope_checksum,
    scope_payload,
)


class ScopeError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _assertion_owners(graph: Mapping[str, Any]) -> dict[str, str]:
    owners: dict[str, str] = {}
    for node in graph.get("nodes") or []:
        key = str(node.get("key") or "")
        for assertion in node.get("assertions") or []:
            if not isinstance(assertion, Mapping):
                continue
            assertion_key = str(
                assertion.get("assertion_key") or assertion.get("key") or ""
            ).strip()
            if assertion_key:
                owners.setdefault(assertion_key, key)
    return owners


def _node_keys(graph: Mapping[str, Any]) -> list[str]:
    return [str(node.get("key")) for node in graph.get("nodes") or []]


def _dependencies(graph: Mapping[str, Any]) -> dict[str, set[str]]:
    keys = set(_node_keys(graph))
    deps: dict[str, set[str]] = {key: set() for key in keys}
    for node in graph.get("nodes") or []:
        key = str(node.get("key"))
        for dep in node.get("depends_on") or []:
            if str(dep) in keys:
                deps[key].add(str(dep))
    for edge in graph.get("edges") or []:
        source, target = str(edge.get("from")), str(edge.get("to"))
        if source in keys and target in keys:
            deps[target].add(source)
    return deps


def _transitive_dependencies(deps: Mapping[str, set[str]], roots: set[str]) -> set[str]:
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        current = stack.pop()
        for dep in deps.get(current, set()):
            if dep not in seen and dep not in roots:
                seen.add(dep)
                stack.append(dep)
    return seen


def build_scope_plan(
    *,
    scope: str,
    graph: Mapping[str, Any],
    mandatory_refs: list[str],
    excluded: list[dict[str, Any]],
    inputs: Mapping[str, Any],
    rule_version: str = RULE_VERSION,
) -> dict[str, Any]:
    """把 mandatory case refs 映射到 graph 节点，计算 related/smoke 三类集合。"""
    keys = set(_node_keys(graph))
    owners = _assertion_owners(graph)
    mandatory_nodes: set[str] = set()
    missing: list[str] = []
    for ref in mandatory_refs:
        text = str(ref)
        if text.startswith("node:"):
            key = text[5:]
            if key in keys:
                mandatory_nodes.add(key)
            else:
                missing.append(text)
        elif text.startswith("assertion:"):
            owner_key = owners.get(text[len("assertion:"):])
            if owner_key:
                mandatory_nodes.add(owner_key)
            else:
                missing.append(text)
        elif text in keys:
            mandatory_nodes.add(text)
        # 其余为 case/需求 ID（P0-xxx），不直接映射到节点，保留在 refs 供报告。
    if missing:
        raise ScopeError("MANDATORY_NODE_MISSING", f"必测引用不在冻结 DAG 中: {sorted(missing)}")
    if not mandatory_nodes:
        raise ScopeError(
            "MANDATORY_SCOPE_EMPTY",
            "mandatory scope 未包含任何 DAG 节点，拒绝创建回归执行",
        )
    deps = _dependencies(graph)
    related = _transitive_dependencies(deps, mandatory_nodes)
    smoke = keys - mandatory_nodes - related
    reasons: dict[str, str] = {}
    for key in sorted(mandatory_nodes):
        reasons[key] = "MANDATORY_FAILED_OR_P0"
    for key in sorted(related):
        reasons[key] = "RELATED_REQUIRED_DEPENDENCY"
    for key in sorted(smoke):
        reasons[key] = "REGRESSION_SMOKE"
    payload = scope_payload(
        scope=scope,
        rule_version=rule_version,
        mandatory_refs=list(mandatory_refs),
        mandatory_node_keys=sorted(mandatory_nodes),
        related_node_keys=sorted(related),
        smoke_node_keys=sorted(smoke),
        excluded=excluded,
        reasons=reasons,
        inputs=dict(inputs),
    )
    payload["checksum_sha256"] = scope_checksum(
        {key: value for key, value in payload.items() if key != "checksum_sha256"}
    )
    return payload


def ensure_scope_snapshot(
    db: Session,
    *,
    project_id: int,
    defect_id: int,
    plan: Mapping[str, Any],
    approved_by: int | None = None,
) -> RegressionScopeSnapshot:
    checksum = str(plan["checksum_sha256"])
    existing = db.scalar(
        select(RegressionScopeSnapshot).where(
            RegressionScopeSnapshot.project_id == int(project_id),
            RegressionScopeSnapshot.defect_id == int(defect_id),
            RegressionScopeSnapshot.checksum_sha256 == checksum,
        )
    )
    if existing is not None:
        return existing
    row = RegressionScopeSnapshot(
        project_id=int(project_id),
        defect_id=int(defect_id),
        scope=str(plan["scope"]),
        rule_version=str(plan["rule_version"]),
        checksum_sha256=checksum,
        mandatory_refs_json=list(plan["mandatory_refs"]),
        mandatory_node_keys_json=list(plan["mandatory_node_keys"]),
        related_node_keys_json=list(plan["related_node_keys"]),
        smoke_node_keys_json=list(plan["smoke_node_keys"]),
        excluded_json=list(plan["excluded"]),
        reasons_json=dict(plan["reasons"]),
        inputs_json=dict(plan["inputs"]),
        approved_by=approved_by,
    )
    db.add(row)
    db.flush()
    return row


def stored_payload(scope_row: RegressionScopeSnapshot) -> dict[str, Any]:
    return scope_payload(
        scope=scope_row.scope,
        rule_version=scope_row.rule_version,
        mandatory_refs=list(scope_row.mandatory_refs_json or []),
        mandatory_node_keys=list(scope_row.mandatory_node_keys_json or []),
        related_node_keys=list(scope_row.related_node_keys_json or []),
        smoke_node_keys=list(scope_row.smoke_node_keys_json or []),
        excluded=list(scope_row.excluded_json or []),
        reasons=dict(scope_row.reasons_json or {}),
        inputs=dict(scope_row.inputs_json or {}),
    )


def verify_scope_snapshot(scope_row: RegressionScopeSnapshot, graph: Mapping[str, Any]) -> dict[str, Any]:
    payload = stored_payload(scope_row)
    recomputed = scope_checksum(payload)
    if recomputed != scope_row.checksum_sha256:
        raise ScopeError("SCOPE_CHECKSUM_MISMATCH", "scope snapshot 内容与 checksum 不一致")
    keys = set(_node_keys(graph))
    missing = [key for key in payload["mandatory_node_keys"] if key not in keys]
    if missing:
        raise ScopeError(
            "MANDATORY_SCOPE_VIOLATION",
            f"mandatory 节点被从执行 DAG 中移除: {sorted(missing)}",
        )
    payload["checksum_sha256"] = recomputed
    return payload


__all__ = [
    "RULE_VERSION",
    "ScopeError",
    "build_scope_plan",
    "ensure_scope_snapshot",
    "stored_payload",
    "verify_scope_snapshot",
]
