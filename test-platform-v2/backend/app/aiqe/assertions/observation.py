"""AUD-007：Driver 产出的结构化 Observation（断言引擎的唯一输入）。

v1.5 §01 AUD-007 第 3 条：Driver 只返回 Observation，Assertion Engine 才计算
PASS/FAIL/BLOCKED/UNKNOWN/ERROR —— 断言不得再写死在 Driver 里。

本模块提供 JSONPath 子集解析（``$.a.b``、``$.a[0]``、``a.b``），不引入第三方依赖；
多结果 JSONPath（``[*]``/递归下降）**不**支持，出现即按非法表达式处理（fail closed）。
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

_JSON_PATH_TOKEN = ("$.", "$")


class InvalidJsonPath(ValueError):
    pass


def parse_json_path(path: str) -> list[str | int]:
    """把 ``$.a.b[0]`` 解析为 ``["a", "b", 0]``；拒绝通配/递归。"""
    raw = str(path or "").strip()
    if not raw:
        raise InvalidJsonPath("path 不能为空")
    if raw.startswith("$"):
        raw = raw[1:]
    if raw.startswith("."):
        raw = raw[1:]
    if not raw:
        return []
    if "*" in raw or ".." in raw or "?" in raw or "(" in raw:
        raise InvalidJsonPath(f"不支持的 JSONPath: {path}")
    tokens: list[str | int] = []
    buffer = ""
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == ".":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            index += 1
            continue
        if char == "[":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            end = raw.index("]", index)
            inner = raw[index + 1 : end].strip()
            if not inner or inner in {"*"}:
                raise InvalidJsonPath(f"不支持的 JSONPath: {path}")
            if (inner.startswith("'") and inner.endswith("'")) or (
                inner.startswith('"') and inner.endswith('"')
            ):
                tokens.append(inner[1:-1])
            else:
                try:
                    tokens.append(int(inner))
                except ValueError as exc:
                    raise InvalidJsonPath(f"非法数组下标: {inner}") from exc
            index = end + 1
            continue
        buffer += char
        index += 1
    if buffer:
        tokens.append(buffer)
    return tokens


def resolve_json_path(data: Any, path: str) -> tuple[bool, Any]:
    """返回 ``(found, value)``；缺失/类型不匹配都返回 ``found=False``（不抛异常）。"""
    tokens = parse_json_path(path)
    current = data
    for token in tokens:
        if isinstance(token, int):
            if isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
                if -len(current) <= token < len(current):
                    current = current[token]
                    continue
                return False, None
            return False, None
        if isinstance(current, Mapping):
            if token in current:
                current = current[token]
                continue
            return False, None
        return False, None
    return True, current


def maybe_json(text: str) -> Any:
    stripped = (text or "").strip()
    if not stripped or stripped[0] not in "{[":
        return None
    try:
        return json.loads(stripped)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True)
class Observation:
    """执行事实的结构化视图（脱敏后）。"""

    source: str
    status_code: int | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    body: Any = None
    text: str = ""
    dom: Mapping[str, Any] | None = None
    db_rows: tuple[Mapping[str, Any], ...] = ()
    events: tuple[Mapping[str, Any], ...] = ()
    timings: Mapping[str, float] = field(default_factory=dict)
    correlation_id: str | None = None
    error: str | None = None
    meta: Mapping[str, Any] = field(default_factory=dict)

    def header(self, name: str) -> tuple[bool, str | None]:
        lowered = str(name or "").lower()
        for key, value in (self.headers or {}).items():
            if str(key).lower() == lowered:
                return True, str(value)
        return False, None

    @classmethod
    def from_http(
        cls,
        *,
        status_code: int | None,
        headers: Mapping[str, str] | None = None,
        text: str = "",
        body: Any | None = None,
        duration_ms: float | None = None,
        correlation_id: str | None = None,
        error: str | None = None,
    ) -> Observation:
        parsed = body if body is not None else maybe_json(text)
        timings = {"duration_ms": float(duration_ms or 0)} if duration_ms is not None else {}
        return cls(
            source="http_response",
            status_code=status_code,
            headers=dict(headers or {}),
            body=parsed,
            text=text or "",
            timings=timings,
            correlation_id=correlation_id,
            error=error,
        )


__all__ = [
    "InvalidJsonPath",
    "Observation",
    "maybe_json",
    "parse_json_path",
    "resolve_json_path",
]
