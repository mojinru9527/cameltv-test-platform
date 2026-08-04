"""隔离守卫 404 契约助手（batch-86 WARN 消化）。

双 404 约定（docs/engineering-standards.md）：
- 隔离/权限/存在性守卫：HTTP 404 是正确契约（不泄露存在性）——必须用本助手断言；
- 业务"查不到"：应断言 HTTP 200 + body code==404，禁止用本助手。
"""
from __future__ import annotations

from typing import Any

_GUARD_NOT_FOUND_STATUS = 404


def assert_guard_404(response: Any, what: str = "资源") -> None:
    """断言隔离守卫返回 HTTP 404（跨项目/权限/存在性守卫的正确契约）。"""
    assert response.status_code == _GUARD_NOT_FOUND_STATUS, (
        f"期望隔离守卫 404（{what}），实际 {getattr(response, 'status_code', '?')}: "
        f"{getattr(response, 'text', '')[:200]}"
    )
