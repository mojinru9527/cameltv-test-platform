"""M2 / TA-011 + AUD-003：RunContext / Variable Store（13 号 §4.8 / §19 TA-011）。

- 变量语法：`${nodes.<node_key>.outputs.<name>}`、`${secrets.<NAME>}`、
  `${secret_handles.<handle_id>}`（AUD-003）；
- 引用只能解析**同一 Run** 内已执行节点的 output_ref（Run scope 隔离）；
- secret 只在执行期从注入的 mapping / Vault 解析，`snapshot()` 一律脱敏，禁止落库/日志；
- `set_output_secure()` 把敏感输出写成 Secret Handle 引用（普通 JSON 只留 handle 元信息）。
"""
from __future__ import annotations

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


class VariableResolutionError(ValueError):
    """变量引用无法解析。"""


class SecretLeakError(ValueError):
    """试图把 secret 写入持久化数据。"""


def _looks_like_secret_ref(value: Any) -> bool:
    return isinstance(value, str) and "${" + SECRET_PREFIX in value


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

    def _node(self, node_key: str) -> NodeRun:
        row = self.db.scalar(
            select(NodeRun).where(
                NodeRun.run_id == self.run_id, NodeRun.node_key == node_key
            )
        )
        if row is None:
            raise VariableResolutionError(f"节点不存在于当前 Run: {node_key}")
        return row

    def output(self, node_key: str) -> dict[str, Any]:
        return dict(self._node(node_key).output_ref or {})

    def set_output(self, node_key: str, values: Mapping[str, Any]) -> None:
        if any(_looks_like_secret_ref(v) for v in values.values()):
            raise SecretLeakError("节点输出不能包含 ${secrets.*} 引用")
        row = self._node(node_key)
        merged = dict(row.output_ref or {})
        merged.update(dict(values))
        row.output_ref = merged
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
            if len(parts) != 4 or parts[2] != "outputs" or not parts[1] or not parts[3]:
                raise VariableResolutionError(f"非法节点变量: {ref}")
            outputs = self.output(parts[1])
            if parts[3] not in outputs:
                raise VariableResolutionError(
                    f"节点 {parts[1]} 未声明输出: {parts[3]}"
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
        """递归解析；整串引用返回原始类型，混合串返回字符串插值。"""
        if isinstance(value, dict):
            return {key: self.resolve(item, secrets=secrets) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item, secrets=secrets) for item in value]
        if not isinstance(value, str):
            return value

        match = VAR_RE.fullmatch(value)
        if match:
            return self._resolve_ref(match.group(1), secrets)

        def replace(part: re.Match[str]) -> str:
            resolved = self._resolve_ref(part.group(1), secrets)
            return resolved if isinstance(resolved, str) else str(resolved)

        return VAR_RE.sub(replace, value)

    def snapshot(self, *, secrets: Mapping[str, str] | None = None) -> dict[str, dict[str, Any]]:
        """可持久化/展示的变量快照：secret 引用与已知 secret 值一律脱敏。"""
        rows = list(
            self.db.scalars(select(NodeRun).where(NodeRun.run_id == self.run_id))
        )
        secret_values = {str(v) for v in (secrets or {}).values() if v}

        def scrub(value: Any) -> Any:
            if isinstance(value, dict):
                return {k: scrub(v) for k, v in value.items()}
            if isinstance(value, list):
                return [scrub(v) for v in value]
            if isinstance(value, str):
                if _looks_like_secret_ref(value):
                    return "***"
                for secret in secret_values:
                    if secret and secret in value:
                        return "***"
            return value

        return {row.node_key: scrub(dict(row.output_ref or {})) for row in rows}
