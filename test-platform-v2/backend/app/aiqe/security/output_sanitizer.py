"""V16-003：统一输出分类与 Secret Handle 写入入口（OutputSanitizer）。

唯一允许把节点输出写入持久化层的组件：

```text
DriverResult.data
  → 输出分类（schema 标记 / 字段名 / 值模式）
  → SECRET：SecretVault.put() → outputs 替换为 vault://<opaque-id>
  → PUBLIC/SENSITIVE：redact_mapping 脱敏
  → assert_persistable()（Handle 感知的 secret 断言）→ NodeRun.outputs_json
```

设计约束：
- 字段名不能作为唯一依据：schema `sensitive: true`、字段名规则、值模式三者任一命中即 SECRET；
- Vault 失败即 fail closed（``SecretVaultUnavailable``/``SecretHandleError`` 上抛）；
- 不记录明文到异常信息；``CaptureResult.secret_values`` 只用于同进程内的证据脱敏；
- consumer scope 由 Workflow DAG 计算（节点的传递下游），禁止调用方随意扩大。
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.aiqe.redaction import CLASSIFIER, REDACTED, SecretLeakError, redact_mapping
from app.aiqe.services import jsonpath_subset
from app.aiqe.services.run_errors import OUTPUT_SCHEMA_MISMATCH, VariableResolutionError
from app.aiqe.services.secret_vault import (
    SecretVault,
    create_secret_handle,
    redacted_reference,
)


class SecretClassification(str, Enum):
    PUBLIC = "PUBLIC"
    SENSITIVE = "SENSITIVE"
    SECRET = "SECRET"


@dataclass
class CaptureResult:
    stored: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    secret_keys: list[str] = field(default_factory=list)
    secret_values: list[str] = field(default_factory=list)
    classifications: dict[str, str] = field(default_factory=dict)


def _iter_child_nodes(graph: Mapping[str, Any], node_key: str) -> list[str]:
    """计算 DAG 中 node_key 的传递下游（允许消费该节点输出的节点集合）。"""
    nodes = [node for node in graph.get("nodes") or [] if isinstance(node, Mapping)]
    children: dict[str, set[str]] = {}
    for node in nodes:
        key = str(node.get("key") or "")
        for dep in node.get("depends_on") or []:
            children.setdefault(str(dep), set()).add(key)
    seen: set[str] = set()
    stack = list(children.get(node_key, set()))
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(children.get(current, set()))
    return sorted(seen)


def _schema_spec(schema: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    """支持两种 schema 写法：扁平 ``{key: {sensitive: true}}`` 与 JSON Schema ``properties``。"""
    if not isinstance(schema, Mapping):
        return None
    spec = schema.get(key)
    if isinstance(spec, Mapping):
        return spec
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        nested = properties.get(key)
        if isinstance(nested, Mapping):
            return nested
    return None


def classify_value(
    key: str,
    value: Any,
    *,
    schema: Mapping[str, Any] | None = None,
) -> tuple[SecretClassification, list[str]]:
    """返回（分类，值中检测到的 secret 明文列表）。"""
    spec = _schema_spec(schema, key)
    marked = bool(isinstance(spec, Mapping) and spec.get("sensitive"))
    if marked:
        return SecretClassification.SECRET, ([value] if isinstance(value, str) and value else [])
    if isinstance(value, str) and value:
        found = CLASSIFIER.find_secrets(value)
        if found:
            return SecretClassification.SECRET, found
        if CLASSIFIER.is_sensitive_key(key):
            return SecretClassification.SECRET, [value]
        return SecretClassification.PUBLIC, []
    if CLASSIFIER.is_sensitive_key(key) and value not in (None, ""):
        # 非字符串敏感字段（dict/list）：递归脱敏，不建 Handle（避免破坏类型契约）。
        return SecretClassification.SENSITIVE, []
    return SecretClassification.PUBLIC, []


class OutputSanitizer:
    """节点输出 → 持久化结构的唯一转换器。"""

    def __init__(
        self,
        db: Session,
        *,
        project_id: int,
        run_id: str,
        vault: SecretVault,
        graph: Mapping[str, Any] | None = None,
        ttl_seconds: int = 900,
    ) -> None:
        self.db = db
        self.project_id = int(project_id)
        self.run_id = str(run_id)
        self.vault = vault
        self.graph = dict(graph or {})
        self.ttl_seconds = int(ttl_seconds)

    def consumer_scope(self, node_key: str) -> list[str]:
        return _iter_child_nodes(self.graph, node_key)

    def capture(
        self,
        node: Any,
        result_data: Mapping[str, Any] | None,
        outputs_spec: Mapping[str, str] | None,
        output_schema: Mapping[str, Any] | None = None,
    ) -> CaptureResult:
        data = dict(result_data or {})
        captured = CaptureResult()
        for name, path in (outputs_spec or {}).items():
            if not isinstance(path, str) or not path:
                raise VariableResolutionError(
                    f"节点 {node.node_key} 的 output {name} 缺少 JSONPath",
                    code=OUTPUT_SCHEMA_MISMATCH,
                )
            if path.startswith("$"):
                found, value = jsonpath_subset.first(data, path)
            elif path in data:
                found, value = True, data[path]
            else:
                found, value = jsonpath_subset.first(data, "$." + path)
            if not found:
                raise VariableResolutionError(
                    f"节点 {node.node_key} 的 output {name} 在 DriverResult 中不存在: {path}",
                    code=OUTPUT_SCHEMA_MISMATCH,
                )
            classification, plaintexts = classify_value(name, value, schema=output_schema)
            captured.raw[str(name)] = value
            captured.classifications[str(name)] = classification.value
            if classification is SecretClassification.SECRET:
                if isinstance(value, str) and value:
                    handle = create_secret_handle(
                        self.db,
                        project_id=self.project_id,
                        run_id=self.run_id,
                        producer_node_run_id=node.id,
                        key_name=str(name),
                        value=value,
                        allowed_consumer_nodes=self.consumer_scope(node.node_key),
                        ttl_seconds=self.ttl_seconds,
                        vault=self.vault,
                        secret_type=(
                            "jwt"
                            if value.startswith("eyJ") and value.count(".") == 2
                            else None
                        ),
                        consumer_scope={
                            "allowed_nodes": self.consumer_scope(node.node_key),
                            "ttl_seconds": self.ttl_seconds,
                        },
                    )
                    captured.stored[str(name)] = redacted_reference(handle)
                    captured.secret_keys.append(str(name))
                    captured.secret_values.append(value)
                else:
                    # 非字符串敏感值：递归脱敏后落库（不建 Handle）。
                    captured.stored[str(name)] = redact_mapping(value)
                continue
            if classification is SecretClassification.SENSITIVE:
                captured.stored[str(name)] = redact_mapping(value)
                continue
            # PUBLIC 值仍可能嵌套敏感字段（例如 headers 里的 Authorization）。
            captured.stored[str(name)] = redact_mapping(value)
        return captured

    def detect_secret_values(
        self,
        result_data: Mapping[str, Any] | None,
        outputs_spec: Mapping[str, str] | None,
        output_schema: Mapping[str, Any] | None = None,
    ) -> list[str]:
        """在证据落库前预扫描输出中的 secret 明文（不创建 Handle）。

        用于把 Driver 动态返回的 token/cookie 纳入同一次执行的 known_secrets，
        避免响应证据（Artifact/日志）在 capture 之前泄漏明文。
        """
        data = dict(result_data or {})
        found: list[str] = []
        for name, path in (outputs_spec or {}).items():
            if not isinstance(path, str) or not path:
                continue
            if path.startswith("$"):
                ok, value = jsonpath_subset.first(data, path)
            elif path in data:
                ok, value = True, data[path]
            else:
                ok, value = jsonpath_subset.first(data, "$." + path)
            if not ok:
                continue
            _classification, plaintexts = classify_value(name, value, schema=output_schema)
            found.extend(item for item in plaintexts if item)
        return sorted(set(found))

    def persist(self, node: Any, captured: CaptureResult) -> dict[str, Any]:
        """写入 NodeRun.outputs_json/output_ref（写入前执行 Handle 感知断言）。"""
        assert_persistable(captured.stored, where=f"node:{node.node_key}:outputs")
        merged = dict(node.outputs_json or {})
        merged.update(captured.stored)
        node.outputs_json = dict(merged)
        node.output_ref = dict(merged)
        self.db.flush()
        return dict(merged)


def _is_secret_reference(value: Mapping[str, Any]) -> bool:
    handle_id = value.get("secret_handle_id")
    if not isinstance(handle_id, str) or not handle_id:
        return False
    ref = str(value.get("secret_ref") or "")
    return ref.startswith("vault://") or ref.startswith("secret://")


def assert_persistable(value: Any, *, where: str = "") -> None:
    """Handle 感知的持久化断言。

    - 合法的 Handle 引用（``secret_handle_id`` + ``vault://``/``secret://``）放行；
    - 字段名命中敏感键但值是脱敏占位（``***``/空）放行；
    - 其余命中值模式或敏感键的实际值 → ``SecretLeakError``（fail closed）。
    """
    leaks = _collect_secret_leaks(value)
    if leaks:
        raise SecretLeakError(f"{where or 'value'} 含疑似 secret 明文: {leaks[:3]}")


def _collect_secret_leaks(value: Any, *, depth: int = 0) -> list[str]:
    if depth > 8:
        return []
    if isinstance(value, Mapping):
        if _is_secret_reference(value):
            return []
        leaks: list[str] = []
        for key, item in list(value.items())[:500]:
            if CLASSIFIER.is_sensitive_key(key) and item not in (None, "", REDACTED):
                if isinstance(item, Mapping) and _is_secret_reference(item):
                    continue
                if isinstance(item, str) and (
                    item.startswith("vault://") or item.startswith("secret://")
                ):
                    continue
                leaks.append(str(key))
                continue
            leaks.extend(_collect_secret_leaks(item, depth=depth + 1))
        return leaks
    if isinstance(value, (list, tuple)):
        leaks = []
        for item in value[:500]:
            leaks.extend(_collect_secret_leaks(item, depth=depth + 1))
        return leaks
    if isinstance(value, str):
        return CLASSIFIER.find_secrets(value)
    return []


__all__ = [
    "CaptureResult",
    "OutputSanitizer",
    "SecretClassification",
    "assert_persistable",
    "classify_value",
]
