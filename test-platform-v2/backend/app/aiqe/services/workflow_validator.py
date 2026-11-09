"""M2 / TA-009：Workflow Graph 校验器（13 号 §6.2）。

覆盖验收要求的四类拒绝：
- 循环依赖；
- 未注册 driver/capability；
- 悬空/非祖先变量引用；
- 非幂等写操作自动 retry。

另含 schema_version、node key 唯一、depends_on/edges 一致性、assertion expected 校验，
以及 canonical checksum（已批准 Workflow 内容固定，规则 7 的基础）。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

VAR_RE = re.compile(r"\$\{nodes\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)\}")
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    node: str | None = None

    def __str__(self) -> str:
        where = f"[{self.node}] " if self.node else ""
        return f"{where}{self.code}: {self.message}"


class WorkflowValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        super().__init__("; ".join(str(i) for i in issues))


def workflow_checksum(graph: dict[str, Any]) -> str:
    """已批准 Workflow 的内容指纹（规则 7）。"""
    canonical = json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _iter_strings(value: Any, path: str = ""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_strings(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_strings(item, f"{path}[{index}]")


def _max_attempts(node: dict[str, Any]) -> int:
    retry = node.get("retry_policy") or {}
    try:
        return int(retry.get("max_attempts", 1) or 1)
    except (TypeError, ValueError):
        return 1


def _is_write(node: dict[str, Any]) -> bool:
    method = str((node.get("input") or {}).get("method", "")).upper()
    return node.get("type") == "cleanup" or method in WRITE_METHODS


def _detect_cycle(deps: dict[str, set[str]]) -> list[str]:
    indegree = {key: len(values) for key, values in deps.items()}
    children: dict[str, list[str]] = {key: [] for key in deps}
    for key, values in deps.items():
        for dep in values:
            if dep in children:
                children[dep].append(key)
    queue = [key for key, degree in indegree.items() if degree == 0]
    seen: list[str] = []
    while queue:
        key = queue.pop()
        seen.append(key)
        for child in children[key]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(seen) == len(deps):
        return []
    return sorted(set(deps) - set(seen))


def validate_workflow(
    graph: dict[str, Any],
    *,
    registered_drivers: set[str],
    registered_capabilities: set[str] | None = None,
) -> None:
    """校验 Workflow；有问题聚合抛 WorkflowValidationError（一次给出全部 issue）。"""
    if not isinstance(graph, dict):
        raise WorkflowValidationError(
            [ValidationIssue("graph_invalid", "workflow 必须是对象")]
        )

    issues: list[ValidationIssue] = []

    def add(code: str, message: str, node: str | None = None) -> None:
        issues.append(ValidationIssue(code=code, message=message, node=node))

    if not isinstance(graph.get("schema_version"), str) or not graph["schema_version"]:
        add("schema_version_missing", "缺少 schema_version")

    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise WorkflowValidationError(
            [ValidationIssue("nodes_missing", "nodes 必须是非空数组")]
        )

    node_map: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            add("node_invalid", f"nodes[{index}] 不是对象")
            continue
        key = node.get("key")
        if not isinstance(key, str) or not key:
            add("node_key_missing", f"nodes[{index}] 缺少 key")
            continue
        if key in node_map:
            add("node_key_duplicate", f"node key 重复: {key}", key)
            continue
        node_map[key] = node

    deps: dict[str, set[str]] = {}
    for key, node in node_map.items():
        raw = node.get("depends_on") or []
        if not isinstance(raw, list):
            add("depends_on_invalid", "depends_on 必须是数组", key)
            deps[key] = set()
            continue
        deps[key] = {str(dep) for dep in raw}
        for dep in deps[key]:
            if dep == key:
                add("node_self_dependency", "节点不能依赖自身", key)
            elif dep not in node_map:
                add("node_dependency_missing", f"depends_on 指向不存在的节点: {dep}", key)

        driver = node.get("driver")
        if not isinstance(driver, str) or not driver:
            add("driver_missing", "缺少 driver", key)
        elif driver not in registered_drivers:
            add("driver_unregistered", f"driver 未注册: {driver}", key)

        capability = node.get("capability")
        if (
            registered_capabilities is not None
            and isinstance(capability, str)
            and capability
            and capability not in registered_capabilities
        ):
            add("capability_unregistered", f"capability 未注册: {capability}", key)

        if _is_write(node) and _max_attempts(node) > 1:
            if not node.get("idempotency_key_expr") and not node.get("compensation_node"):
                add(
                    "non_idempotent_retry",
                    "写操作 max_attempts>1 必须声明 idempotency_key_expr 或 compensation_node",
                    key,
                )

        assertions = node.get("assertions") or []
        if not isinstance(assertions, list):
            add("assertions_invalid", "assertions 必须是数组", key)
        else:
            for assertion in assertions:
                if not isinstance(assertion, dict):
                    add("assertion_invalid", "assertion 必须是对象", key)
                    continue
                if assertion.get("type") == "exploratory":
                    continue
                if "expected" not in assertion and "expected_ref" not in assertion:
                    add(
                        "assertion_expected_missing",
                        f"assertion {assertion.get('key', '?')} 缺少 expected/expected_ref",
                        key,
                    )

    cycle = _detect_cycle(deps)
    if cycle:
        add("dependency_cycle", f"存在循环依赖: {' -> '.join(cycle)}")

    # edges 必须与 depends_on 一致（to 依赖 from）
    edges = graph.get("edges") or []
    if not isinstance(edges, list):
        add("edges_invalid", "edges 必须是数组")
        edges = []
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            add("edge_invalid", f"edges[{index}] 不是对象")
            continue
        source, target = edge.get("from"), edge.get("to")
        if source not in node_map or target not in node_map:
            add("edge_endpoint_unknown", f"edge 端点不存在: {source} -> {target}")
        elif source not in deps.get(target, set()):
            add(
                "edge_not_in_depends_on",
                f"edge {source}->{target} 未出现在 {target}.depends_on",
                str(target),
            )

    # 变量引用：节点必须是目标节点的传递祖先，且输出已声明
    def ancestors(key: str) -> set[str]:
        seen: set[str] = set()
        stack = list(deps.get(key, set()))
        while stack:
            current = stack.pop()
            if current in seen or current not in node_map:
                continue
            seen.add(current)
            stack.extend(deps.get(current, set()))
        return seen

    for key, node in node_map.items():
        payload = {
            "input": node.get("input"),
            "assertions": node.get("assertions"),
            "idempotency_key_expr": node.get("idempotency_key_expr"),
        }
        for path, text in _iter_strings(payload):
            for ref_node, ref_output in VAR_RE.findall(text):
                if ref_node not in node_map:
                    add("variable_node_unknown", f"{path}: 未知节点 {ref_node}", key)
                    continue
                if ref_node not in ancestors(key):
                    add(
                        "variable_node_not_ancestor",
                        f"{path}: {ref_node} 不是 {key} 的祖先",
                        key,
                    )
                outputs = node_map[ref_node].get("outputs") or {}
                if isinstance(outputs, dict) and ref_output not in outputs:
                    add(
                        "variable_output_unknown",
                        f"{path}: {ref_node} 未声明输出 {ref_output}",
                        key,
                    )

    if issues:
        raise WorkflowValidationError(issues)
