"""严格 JSONPath 子集（无外部依赖，行为固定可审计）。

支持：
- `$` 根；
- `.name` / `['name']` / `["name"]`；
- `[0]` / `[-1]` / `[*]`；
- `..name` 递归下降；
- `.*` 对象/数组成员。

不支持过滤器 `[?(...)]`、切片和函数。任何未识别语法抛 `JsonPathError`，
而不是悄悄返回 None——断言路径写错必须显式报错。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_NAME = re.compile(r"[A-Za-z0-9_@-]+")
_BRACKET_QUOTED = re.compile(r"\[['\"]([^'\"]+)['\"]\]")
_BRACKET_INDEX = re.compile(r"\[(-?\d+)\]")


class JsonPathError(ValueError):
    pass


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str | None = None
    index: int | None = None


def _parse(path: str) -> list[_Token]:
    if not isinstance(path, str) or not path.strip():
        raise JsonPathError("JSONPath 不能为空")
    cursor = path.strip()
    if not cursor.startswith("$"):
        raise JsonPathError("JSONPath 必须以 $ 开头")
    cursor = cursor[1:]
    tokens: list[_Token] = []
    while cursor:
        if cursor.startswith(".."):
            cursor = cursor[2:]
            match = _NAME.match(cursor)
            if not match:
                raise JsonPathError(f"递归下降缺少字段名: {path}")
            tokens.append(_Token("recursive", match.group(0)))
            cursor = cursor[match.end() :]
            continue
        if cursor.startswith("."):
            cursor = cursor[1:]
            if cursor.startswith("*"):
                tokens.append(_Token("wildcard"))
                cursor = cursor[1:]
                continue
            match = _NAME.match(cursor)
            if not match:
                raise JsonPathError(f"非法字段访问: {path}")
            tokens.append(_Token("child", match.group(0)))
            cursor = cursor[match.end() :]
            continue
        quoted = _BRACKET_QUOTED.match(cursor)
        if quoted:
            tokens.append(_Token("child", quoted.group(1)))
            cursor = cursor[quoted.end() :]
            continue
        index = _BRACKET_INDEX.match(cursor)
        if index:
            tokens.append(_Token("index", index=int(index.group(1))))
            cursor = cursor[index.end() :]
            continue
        if cursor.startswith("[*]"):
            tokens.append(_Token("wildcard"))
            cursor = cursor[3:]
            continue
        raise JsonPathError(f"不支持的 JSONPath 语法: {cursor[:24]!r}（完整: {path}）")
    return tokens


def _recursive_values(node: Any, name: str, out: list[Any]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key) == name:
                out.append(value)
            _recursive_values(value, name, out)
    elif isinstance(node, list):
        for item in node:
            _recursive_values(item, name, out)


def select(data: Any, path: str) -> list[Any]:
    """返回全部匹配值（按文档顺序）。"""
    tokens = _parse(path)
    nodes: list[Any] = [data]
    for token in tokens:
        next_nodes: list[Any] = []
        for node in nodes:
            if token.kind == "child":
                if isinstance(node, dict) and token.value in node:
                    next_nodes.append(node[token.value])
                elif isinstance(node, list) and token.value is not None and token.value.isdigit():
                    idx = int(token.value)
                    if -len(node) <= idx < len(node):
                        next_nodes.append(node[idx])
            elif token.kind == "index":
                if isinstance(node, list):
                    idx = int(token.index or 0)
                    if -len(node) <= idx < len(node):
                        next_nodes.append(node[idx])
                elif isinstance(node, dict):
                    key = str(token.index)
                    if key in node:
                        next_nodes.append(node[key])
            elif token.kind == "wildcard":
                if isinstance(node, dict):
                    next_nodes.extend(node.values())
                elif isinstance(node, list):
                    next_nodes.extend(node)
            elif token.kind == "recursive":
                _recursive_values(node, str(token.value), next_nodes)
        nodes = next_nodes
        if not nodes:
            break
    return nodes


def first(data: Any, path: str) -> tuple[bool, Any]:
    values = select(data, path)
    if not values:
        return False, None
    return True, values[0]


def validate_path(path: str) -> None:
    _parse(path)
