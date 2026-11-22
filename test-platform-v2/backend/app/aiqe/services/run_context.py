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
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.redaction import CLASSIFIER, redact_mapping
from app.aiqe.schemas.contracts import ResolvedInput, SourceRef
from app.aiqe.security.output_sanitizer import OutputSanitizer, assert_persistable
from app.aiqe.services import jsonpath_subset
from app.aiqe.services.run_errors import (
    FIXTURE_NOT_FOUND,
    OUTPUT_SCHEMA_MISMATCH,
    SECRET_UNAVAILABLE,
    VARIABLE_NOT_ANCESTOR,
    VARIABLE_NOT_FOUND,
    SecretLeakError,
    VariableResolutionError,
)
from app.aiqe.services.secret_vault import (
    SecretVault,
    create_secret_handle,
    redacted_reference,
    resolve_secret_handle,
)

VAR_RE = re.compile(r"\$\{([^{}]+)\}")
SECRET_PREFIX = "secrets."


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
        handle_resolver: Callable[[str, str], str] | None = None,
        vault: SecretVault | None = None,
        project_id: int | None = None,
        secret_ttl_seconds: int = 900,
    ) -> None:
        self.db = db
        self.run_id = run_id
        self.vault = vault
        self.project_id = int(project_id) if project_id is not None else None
        self.secret_ttl_seconds = int(secret_ttl_seconds)
        if handle_resolver is None and vault is not None:
            handle_resolver = self._default_handle_resolver
        self._handle_resolver = handle_resolver
        self._consumer_node_key = ""
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

    # ── secret dependency wiring ──────────────────────────────────────
    def _project_id(self) -> int:
        if self.project_id is not None:
            return self.project_id
        run = self.db.get(TestRun, self.run_id)
        if run is None:
            raise VariableResolutionError(
                "Run 不存在，无法解析 Secret Handle", code=SECRET_UNAVAILABLE
            )
        self.project_id = int(run.project_id)
        return self.project_id

    def _default_handle_resolver(self, handle_id: str, consumer_node_key: str) -> str:
        value = resolve_secret_handle(
            self.db,
            handle_id,
            project_id=self._project_id(),
            run_id=self.run_id,
            consumer_node_key=consumer_node_key,
            vault=self.vault,
        )
        # 解析出的明文同样进入 known_secrets，供证据/日志脱敏。
        self.last_secret_values.append(value)
        return value

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
        sanitized = redact_mapping(dict(values))
        assert_persistable(sanitized, where=f"node:{node_key}:outputs")
        row = self._node(node_key)
        merged = dict(row.outputs_json or row.output_ref or {})
        merged.update(sanitized)
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
                self.last_secret_values.append(value)
                continue
            stored[key] = redact_mapping(value)
        assert_persistable(stored, where=f"node:{node_key}:outputs")
        merged = dict(row.outputs_json or row.output_ref or {})
        merged.update(stored)
        row.outputs_json = dict(merged)
        row.output_ref = dict(merged)
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
        """解析节点输入；`${secret_handles.x}` 与敏感输出按 consumer scope 取值。"""
        self._consumer_node_key = str(node_key)
        self._current_node_key = str(node_key)
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
            if isinstance(value, Mapping) and value.get("secret_handle_id"):
                return self._resolve_handle(str(value["secret_handle_id"]))
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
        if ref.startswith("secret_handles."):
            handle_id = ref[len("secret_handles.") :].strip()
            if not handle_id:
                raise VariableResolutionError("secret handle id 不能为空")
            return self._resolve_handle(handle_id)
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
        # Handle 解析必须按“当前消费者节点”校验 scope（不能留空绕过白名单）。
        self._consumer_node_key = node_key
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
        # 先按字段名/值模式脱敏，再按已知 secret 值替换（字面量 password 也不能落库）。
        sanitized = redact_mapping(dict(resolved.values or {}))
        sanitized = _scrub_values(sanitized, secret_values)
        assert_persistable(sanitized, where=f"node:{node.node_key}:resolved_input")
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
        """按节点声明的 outputs 提取结构化输出并做统一分类/Handle 化。

        V16-003：返回值是**已脱敏/Handle 化**的存储值（不是 Driver 原始值）。
        """
        if self.vault is None:
            raise SecretLeakError(
                "RunContext 未注入 SecretVault：禁止在无 Vault 时持久化节点输出"
            )
        sanitizer = OutputSanitizer(
            self.db,
            project_id=self._project_id(),
            run_id=self.run_id,
            vault=self.vault,
            graph=self.graph,
            ttl_seconds=self.secret_ttl_seconds,
        )
        data = getattr(result, "data", None) or {}
        captured = sanitizer.capture(node, data, outputs_spec, output_schema)
        if output_schema:
            # schema 校验针对 Driver 返回的原始值（Handle 是存储表示，不是业务值）。
            _validate_output_schema(dict(captured.raw), output_schema)
        stored = sanitizer.persist(node, captured)
        self.last_secret_values.extend(captured.secret_values)
        return stored

    def preview_secret_values(
        self,
        result: Any,
        outputs_spec: Mapping[str, str] | None,
        output_schema: Mapping[str, Any] | None = None,
    ) -> list[str]:
        """预扫描输出中的 secret 明文（证据落库前纳入 known_secrets）。"""
        if self.vault is None:
            return []
        sanitizer = OutputSanitizer(
            self.db,
            project_id=self._project_id(),
            run_id=self.run_id,
            vault=self.vault,
            graph=self.graph,
            ttl_seconds=self.secret_ttl_seconds,
        )
        return sanitizer.detect_secret_values(
            getattr(result, "data", None) or {}, outputs_spec, output_schema
        )

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
