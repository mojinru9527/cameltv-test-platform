"""M2 / TA-011：RunContext / Variable Store（13 号 §4.8 / §19 TA-011）。

- 变量语法：`${nodes.<node_key>.outputs.<name>}`、`${secrets.<NAME>}`；
- 引用只能解析**同一 Run** 内已执行节点的 output_ref（Run scope 隔离）；
- secret 只在执行期从注入的 mapping 解析，`snapshot()` 一律脱敏，禁止落库/日志；
- 节点输出写入 `node_runs.output_ref`（JSON），供后续节点引用。
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun

VAR_RE = re.compile(r"\$\{([^{}]+)\}")
SECRET_PREFIX = "secrets."


class VariableResolutionError(ValueError):
    """变量引用无法解析。"""


class SecretLeakError(ValueError):
    """试图把 secret 写入持久化数据。"""


def _looks_like_secret_ref(value: Any) -> bool:
    return isinstance(value, str) and "${" + SECRET_PREFIX in value


class RunContext:
    def __init__(self, db: Session, run_id: str) -> None:
        self.db = db
        self.run_id = run_id

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
            return outputs[parts[3]]
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
