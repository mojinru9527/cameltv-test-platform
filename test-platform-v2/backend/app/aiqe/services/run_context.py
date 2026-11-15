"""RunContext v1.4（FIX-001 / TA-011）。

- 一个 Context 只属于一个 `run_id`；跨 Run 完全隔离；
- 支持 `${nodes.<key>.outputs.<name>}`、`${FIXTURE:<key>}`、`${SECRET:<key>}`、
  `${ENV:<key>}`，并兼容旧语法 `${secrets.<NAME>}`；
- 引用的节点必须是当前节点的祖先，且输出必须由该节点声明；
- 解析结果产出版本化 `ResolvedInput`，带 source_refs；secret 只保留 key，
  持久化前把值替换为 `***`，真实值只在执行器内存中；
- 节点完成时按声明的 outputs 从 DriverResult.data 做 JSONPath 提取，写入
  `outputs_json`（同时镜像到 `output_ref` 兼容旧 UI）；
- 缺少变量 / secret / fixture / 类型不匹配时抛带错误码的异常，由调度器置 BLOCKED。
"""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun
from app.aiqe.schemas.contracts import ResolvedInput, SourceRef
from app.aiqe.services import jsonpath_subset

VAR_RE = re.compile(r"\$\{([^{}]+)\}")
SECRET_PREFIX = "secrets."

VARIABLE_NOT_FOUND = "VARIABLE_NOT_FOUND"
VARIABLE_NOT_ANCESTOR = "VARIABLE_NOT_ANCESTOR"
SECRET_UNAVAILABLE = "SECRET_UNAVAILABLE"
FIXTURE_NOT_FOUND = "FIXTURE_NOT_FOUND"
OUTPUT_SCHEMA_MISMATCH = "OUTPUT_SCHEMA_MISMATCH"


class VariableResolutionError(ValueError):
    """变量引用无法解析；`code` 用于 Run/Node 错误分类。"""

    def __init__(self, message: str, *, code: str = VARIABLE_NOT_FOUND) -> None:
        self.code = code
        super().__init__(message)


class SecretLeakError(ValueError):
    """试图把 secret 写入持久化数据。"""


class SecretProvider(Protocol):
    def get(self, key: str) -> str | None: ...


class MappingSecretProvider:
    def __init__(self, values: Mapping[str, str] | None = None) -> None:
        self._values = {str(key): str(value) for key, value in (values or {}).items()}

    def get(self, key: str) -> str | None:
        return self._values.get(str(key))


class EnvSecretProvider:
    """从 Runner 环境变量读取：`AIQE_SECRET_<KEY>`，或 JSON 形式 `AIQE_SECRETS_JSON`。"""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = dict(environ or os.environ)
        self._json: dict[str, str] = {}
        raw = self._environ.get("AIQE_SECRETS_JSON")
        if raw:
            import json

            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    self._json = {str(k): str(v) for k, v in parsed.items()}
            except (TypeError, ValueError):
                self._json = {}

    def get(self, key: str) -> str | None:
        if key in self._json:
            return self._json[key]
        return self._environ.get(f"AIQE_SECRET_{key}") or self._environ.get(
            f"AIQE_SECRET_{key.upper()}"
        )


def _looks_like_secret_ref(value: Any) -> bool:
    return isinstance(value, str) and (
        "${" + SECRET_PREFIX in value or "${SECRET:" in value
    )


class RunContext:
    def __init__(
        self,
        db: Session,
        run_id: str,
        *,
        graph: Mapping[str, Any] | None = None,
        secrets: Mapping[str, str] | SecretProvider | None = None,
        fixtures: Mapping[str, Any] | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.db = db
        self.run_id = run_id
        self.graph = dict(graph or {})
        if isinstance(secrets, Mapping):
            self.secret_provider: SecretProvider = MappingSecretProvider(secrets)
        elif secrets is not None:
            self.secret_provider = secrets
        else:
            self.secret_provider = EnvSecretProvider(environ)
        self.fixtures = dict(fixtures or {})
        self.environ = dict(environ or os.environ)
        self.last_source_refs: list[SourceRef] = []
        self.last_secret_values: list[str] = []
        self._current_node_key: str | None = None

    # ── node access ────────────────────────────────────────────────────
    def _node(self, node_key: str) -> NodeRun:
        row = self.db.scalar(
            select(NodeRun).where(
                NodeRun.run_id == self.run_id, NodeRun.node_key == node_key
            )
        )
        if row is None:
            raise VariableResolutionError(
                f"节点不存在于当前 Run: {node_key}", code=VARIABLE_NOT_FOUND
            )
        return row

    def output(self, node_key: str) -> dict[str, Any]:
        row = self._node(node_key)
        return dict(row.outputs_json or row.output_ref or {})

    def set_output(self, node_key: str, values: Mapping[str, Any]) -> None:
        if any(_looks_like_secret_ref(v) for v in values.values()):
            raise SecretLeakError("节点输出不能包含 ${SECRET:*} / ${secrets.*} 引用")
        row = self._node(node_key)
        merged = dict(row.outputs_json or row.output_ref or {})
        merged.update(dict(values))
        row.outputs_json = merged
        row.output_ref = dict(merged)
        self.db.flush()

    # ── resolution ─────────────────────────────────────────────────────
    def _ancestors(self, node_key: str) -> set[str]:
        if not self.graph:
            return set()
        deps = {
            str(node.get("key")): [str(dep) for dep in (node.get("depends_on") or [])]
            for node in self.graph.get("nodes", [])
        }
        seen: set[str] = set()
        stack = list(deps.get(node_key, []))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(deps.get(current, []))
        return seen

    def _secret(self, key: str) -> str:
        value = self.secret_provider.get(key)
        if value is None:
            raise VariableResolutionError(
                f"secret 未注入或已过期: {key}", code=SECRET_UNAVAILABLE
            )
        self.last_secret_values.append(value)
        return value

    def _resolve_ref(self, ref: str) -> Any:
        if ref.startswith("nodes."):
            parts = ref.split(".")
            if len(parts) < 4 or parts[2] != "outputs" or not parts[1] or not parts[3]:
                raise VariableResolutionError(f"非法节点变量: {ref}")
            node_key, output_name = parts[1], parts[3]
            if self.graph and self._current_node_key:
                if node_key not in self._ancestors(self._current_node_key):
                    raise VariableResolutionError(
                        f"{self._current_node_key} 引用了非祖先节点 {node_key}",
                        code=VARIABLE_NOT_ANCESTOR,
                    )
            outputs = self.output(node_key)
            if output_name not in outputs:
                raise VariableResolutionError(
                    f"节点 {node_key} 未声明/未产出输出: {output_name}",
                    code=VARIABLE_NOT_FOUND,
                )
            value: Any = outputs[output_name]
            # 支持 `${nodes.A.outputs.data.id}` 的深层取值（只读，不改变声明校验）。
            if len(parts) > 4:
                sub_path = "$." + ".".join(parts[4:])
                found, value = jsonpath_subset.first(value, sub_path)
                if not found:
                    raise VariableResolutionError(
                        f"输出 {node_key}.{output_name} 中不存在路径 {sub_path}",
                        code=VARIABLE_NOT_FOUND,
                    )
            self.last_source_refs.append(
                SourceRef(
                    kind="node_output",
                    ref=ref,
                    node_key=node_key,
                    output=output_name,
                )
            )
            return value
        if ref.startswith(SECRET_PREFIX) or ref.upper().startswith("SECRET:"):
            key = ref[len(SECRET_PREFIX) :] if ref.startswith(SECRET_PREFIX) else ref.split(":", 1)[1]
            key = key.strip()
            if not key:
                raise VariableResolutionError(f"非法 secret 引用: {ref}", code=SECRET_UNAVAILABLE)
            value = self._secret(key)
            self.last_source_refs.append(SourceRef(kind="secret", ref=f"SECRET:{key}"))
            return value
        if ref.upper().startswith("FIXTURE:"):
            key = ref.split(":", 1)[1].strip()
            if key not in self.fixtures:
                raise VariableResolutionError(
                    f"fixture 不存在: {key}", code=FIXTURE_NOT_FOUND
                )
            value = self.fixtures[key]
            self.last_source_refs.append(SourceRef(kind="fixture", ref=f"FIXTURE:{key}"))
            return value
        if ref.upper().startswith("ENV:"):
            key = ref.split(":", 1)[1].strip()
            if key not in self.environ:
                raise VariableResolutionError(
                    f"环境变量不存在: {key}", code=VARIABLE_NOT_FOUND
                )
            value = self.environ[key]
            self.last_source_refs.append(SourceRef(kind="env", ref=f"ENV:{key}"))
            return value
        raise VariableResolutionError(f"未知变量命名空间: {ref}")

    def resolve(self, value: Any, *, secrets: Mapping[str, str] | None = None) -> Any:
        """递归解析；整串引用返回原始类型，混合串返回字符串插值。

        `secrets` 只在本次调用生效，不会污染后续调用（旧测试要求无注入时报错）。
        """
        if secrets is None:
            return self._resolve_value(value)
        previous = self.secret_provider
        self.secret_provider = MappingSecretProvider(secrets)
        try:
            return self._resolve_value(value)
        finally:
            self.secret_provider = previous

    def _resolve_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(item) for item in value]
        if not isinstance(value, str):
            return value

        match = VAR_RE.fullmatch(value)
        if match:
            return self._resolve_ref(match.group(1))

        def replace(part: re.Match[str]) -> str:
            resolved = self._resolve_ref(part.group(1))
            return resolved if isinstance(resolved, str) else str(resolved)

        return VAR_RE.sub(replace, value)

    def resolve_node_input(
        self, node_key: str, raw_input: Mapping[str, Any] | None
    ) -> ResolvedInput:
        """解析节点输入并生成可审计的 ResolvedInput。"""
        ancestors = self._ancestors(node_key)
        if self.graph and ancestors:
            # 先做静态祖先校验：引用了非祖先节点必须显式失败，而不是执行时才发现。
            for _, text in _iter_strings(dict(raw_input or {})):
                match = re.fullmatch(r"\$\{nodes\.([^.}]+)\.outputs\.[^}]+\}", text)
                if match and match.group(1) not in ancestors:
                    raise VariableResolutionError(
                        f"{node_key} 引用了非祖先节点 {match.group(1)}",
                        code=VARIABLE_NOT_ANCESTOR,
                    )
        self.last_source_refs = []
        self.last_secret_values = []
        self._current_node_key = node_key
        values = self.resolve(dict(raw_input or {}))
        secret_keys = sorted(
            {
                ref.ref.split(":", 1)[1]
                for ref in self.last_source_refs
                if ref.kind == "secret"
            }
        )
        return ResolvedInput(
            values=dict(values or {}),
            source_refs=list(self.last_source_refs),
            secret_keys=secret_keys,
        )

    def persist_resolved_input(self, node: NodeRun, resolved: ResolvedInput) -> None:
        """持久化脱敏后的解析输入；真实 secret 值不落盘。"""
        secret_values = sorted({value for value in self.last_secret_values if value})
        sanitized = _scrub_values(resolved.values, secret_values)
        node.resolved_input_json = dict(sanitized or {})
        node.secret_keys_json = list(resolved.secret_keys)
        node.source_refs_json = [
            ref.model_dump(mode="json") for ref in resolved.source_refs
        ]
        self.db.flush()

    # ── outputs ────────────────────────────────────────────────────────
    def capture_node_outputs(
        self,
        node: NodeRun,
        result: Any,
        outputs_spec: Mapping[str, str] | None,
        output_schema: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """按节点声明的 outputs 从 DriverResult.data 提取结构化输出。"""
        data = getattr(result, "data", None) or {}
        outputs: dict[str, Any] = {}
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
            outputs[name] = value
        if output_schema:
            _validate_output_schema(outputs, output_schema)
        merged = dict(node.outputs_json or {})
        merged.update(outputs)
        node.outputs_json = merged
        node.output_ref = dict(merged)
        self.db.flush()
        return outputs

    def snapshot(self, *, secrets: Mapping[str, str] | None = None) -> dict[str, dict[str, Any]]:
        """可持久化/展示的变量快照：secret 引用与已知 secret 值一律脱敏。"""
        if secrets is not None:
            self.secret_provider = MappingSecretProvider(secrets)
        rows = list(
            self.db.scalars(select(NodeRun).where(NodeRun.run_id == self.run_id))
        )
        return {
            row.node_key: _scrub_values(
                dict(row.outputs_json or row.output_ref or {}), []
            )
            for row in rows
        }


def _iter_strings(value: Any, path: str = ""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_strings(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_strings(item, f"{path}[{index}]")


def _scrub_values(value: Any, secret_values: list[str]) -> Any:
    if isinstance(value, dict):
        return {key: _scrub_values(item, secret_values) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub_values(item, secret_values) for item in value]
    if isinstance(value, str):
        if _looks_like_secret_ref(value):
            return "***"
        for secret in secret_values:
            if secret and secret in value:
                return "***"
    return value


def _validate_output_schema(outputs: dict[str, Any], schema: Mapping[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except Exception as exc:  # pragma: no cover
        raise VariableResolutionError(
            f"jsonschema 不可用: {exc}", code=OUTPUT_SCHEMA_MISMATCH
        ) from exc
    errors = sorted(
        Draft202012Validator(dict(schema)).iter_errors(outputs),
        key=lambda item: list(item.path),
    )
    if errors:
        first = errors[0]
        raise VariableResolutionError(
            f"output schema 不匹配: {'/'.join(str(p) for p in first.path)}: {first.message}",
            code=OUTPUT_SCHEMA_MISMATCH,
        )
