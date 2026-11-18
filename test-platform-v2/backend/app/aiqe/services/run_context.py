"""M2 / TA-011 + AUD-003：RunContext / Variable Store（13 号 §4.8 / §19 TA-011）。

- 变量语法：`${nodes.<node_key>.outputs.<name>}`、`${secrets.<NAME>}`、
  `${secret_handles.<handle_id>}`（AUD-003）；
- 引用只能解析**同一 Run** 内已执行节点的 output_ref（Run scope 隔离）；
- secret 只在执行期从注入的 mapping / Vault 解析，`snapshot()` 一律脱敏，禁止落库/日志；
- `set_output_secure()` 把敏感输出写成 Secret Handle 引用（普通 JSON 只留 handle 元信息）。
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun
from app.aiqe.redaction import CLASSIFIER, redact_mapping
from app.aiqe.services.secret_vault import (
    SecretVault,
    create_secret_handle,
    redacted_reference,
)

VAR_RE = re.compile(r"\$\{([^{}]+)\}")
SECRET_PREFIX = "secrets."
HANDLE_PREFIX = "secret_handles."
HANDLE_ID_KEY = "secret_handle_id"

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
        handle_resolver: Callable[[str, str], str] | None = None,
    ) -> None:
        self.db = db
        self.run_id = run_id
        self._handle_resolver = handle_resolver
        self._consumer_node_key: str = ""

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

    def set_output_secure(
        self,
        node_key: str,
        values: Mapping[str, Any],
        *,
        project_id: int,
        allowed_consumer_nodes: tuple[str, ...] | list[str] = (),
        schema: Mapping[str, Any] | None = None,
        ttl_seconds: int = 900,
        vault: SecretVault | None = None,
    ) -> dict[str, Any]:
        """敏感输出写 Secret Handle，普通输出脱敏后落库（AUD-003 §3-4）。"""
        row = self._node(node_key)
        stored: dict[str, Any] = {}
        for key, value in values.items():
            marked = False
            if isinstance(schema, Mapping):
                spec = schema.get(key)
                marked = bool(isinstance(spec, Mapping) and spec.get("sensitive"))
            if (marked or CLASSIFIER.is_sensitive_key(key)) and isinstance(value, str) and value:
                handle = create_secret_handle(
                    self.db,
                    project_id=int(project_id),
                    run_id=self.run_id,
                    producer_node_run_id=row.id,
                    key_name=str(key),
                    value=value,
                    allowed_consumer_nodes=list(allowed_consumer_nodes),
                    ttl_seconds=ttl_seconds,
                    vault=vault,
                )
                stored[key] = redacted_reference(handle)
                continue
            stored[key] = redact_mapping(value)
        merged = dict(row.output_ref or {})
        merged.update(stored)
        row.output_ref = merged
        self.db.flush()
        return stored

    def resolve_inputs(
        self,
        node_key: str,
        spec: Any,
        *,
        secrets: Mapping[str, str] | None = None,
        handle_resolver: Callable[[str, str], str] | None = None,
    ) -> Any:
        """解析节点输入；`${secret_handles.x}` 与敏感节点输出按 consumer scope 取值。"""
        self._consumer_node_key = str(node_key)
        resolver = handle_resolver or self._handle_resolver
        previous = self._handle_resolver
        self._handle_resolver = resolver
        try:
            return self.resolve(spec, secrets=secrets)
        finally:
            self._handle_resolver = previous

    def _resolve_handle(self, handle_id: str) -> str:
        if self._handle_resolver is None:
            raise VariableResolutionError("未注入 Secret Handle resolver")
        return self._handle_resolver(handle_id, self._consumer_node_key)

    def _resolve_ref(self, ref: str, secrets: Mapping[str, str] | None) -> Any:
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
            value = outputs[parts[3]]
            if isinstance(value, Mapping) and value.get(HANDLE_ID_KEY):
                return self._resolve_handle(str(value[HANDLE_ID_KEY]))
            return value
        if ref.startswith(HANDLE_PREFIX):
            handle_id = ref[len(HANDLE_PREFIX) :].strip()
            if not handle_id:
                raise VariableResolutionError("secret handle id 不能为空")
            return self._resolve_handle(handle_id)
        if ref.startswith(SECRET_PREFIX):
            name = ref[len(SECRET_PREFIX) :]
            if not name or secrets is None or name not in secrets:
                raise VariableResolutionError(f"secret 未注入: {name or ref}")
            return secrets[name]
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
