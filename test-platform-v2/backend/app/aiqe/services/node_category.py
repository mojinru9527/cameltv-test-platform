"""V16-009：节点类别与业务 Oracle 判定（Run/Quality Gate/Validator 共用）。

- ``BUSINESS``：必有业务 Oracle，只有它能让 Run PASS；
- ``SETUP`` / ``CLEANUP``：允许无断言，但不得贡献业务 PASS；
- ``OBSERVE``：只采集证据，不得作为业务成功依据。

类别来源优先级：节点显式 ``category`` > driver 推导（动作类 driver 默认 BUSINESS）。
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CATEGORY_BUSINESS = "BUSINESS"
CATEGORY_SETUP = "SETUP"
CATEGORY_CLEANUP = "CLEANUP"
CATEGORY_OBSERVE = "OBSERVE"
VALID_CATEGORIES = frozenset(
    {CATEGORY_BUSINESS, CATEGORY_SETUP, CATEGORY_CLEANUP, CATEGORY_OBSERVE}
)

#: 动作类 driver：默认按业务节点要求 Oracle。
ACTION_DRIVERS = frozenset(
    {
        "http",
        "httpx",
        "api",
        "playwright",
        "web",
        "ui",
        "db",
        "db_readonly",
        "database",
        "appium",
        "android",
        "mobile",
        "miniapp",
        "device",
        "external_e2e",
        "e2e",
    }
)
#: 合法的 Oracle 层级（与 assertion_service 一致）。
ORACLE_LAYERS = frozenset({"REQ", "STD", "PATTERN"})


def node_category(node_def: Mapping[str, Any] | None, *, driver: str = "") -> str:
    payload = dict(node_def or {})
    explicit = str(payload.get("category") or payload.get("node_category") or "").strip().upper()
    if explicit in VALID_CATEGORIES:
        return explicit
    # 兼容历史写法：node.type = setup/cleanup/observe。
    legacy_type = str(payload.get("type") or "").strip().upper()
    if legacy_type in VALID_CATEGORIES:
        return legacy_type
    driver_key = str(driver or payload.get("driver") or "").strip().lower()
    if driver_key in ACTION_DRIVERS:
        return CATEGORY_BUSINESS
    return CATEGORY_SETUP


def _assertion_is_business_oracle(assertion: Mapping[str, Any]) -> bool:
    if not isinstance(assertion, Mapping):
        return False
    if str(assertion.get("type") or "") == "exploratory":
        return False
    if not str(assertion.get("type") or "").strip():
        return False
    if "expected" not in assertion and "expected_ref" not in assertion:
        return False
    layer = str(assertion.get("oracle_layer") or "").strip().upper()
    if layer and layer not in ORACLE_LAYERS:
        return False
    return True


def has_business_oracle(
    assertions: Any,
    input_ref: Mapping[str, Any] | None = None,
) -> bool:
    """是否存在有效业务 Oracle（断言或历史 expected_status/expect_text）。"""
    for assertion in assertions or []:
        if _assertion_is_business_oracle(assertion):
            return True
    legacy = dict(input_ref or {})
    if legacy.get("expected_status") is not None:
        try:
            int(legacy["expected_status"])
        except (TypeError, ValueError):
            return False
        return True
    if str(legacy.get("expect_text") or "").strip():
        return True
    return False


def graph_node_by_key(graph: Mapping[str, Any] | None, node_key: str) -> dict[str, Any]:
    for node in (graph or {}).get("nodes") or []:
        if isinstance(node, Mapping) and str(node.get("key")) == str(node_key):
            return dict(node)
    return {}


__all__ = [
    "ACTION_DRIVERS",
    "CATEGORY_BUSINESS",
    "CATEGORY_CLEANUP",
    "CATEGORY_OBSERVE",
    "CATEGORY_SETUP",
    "ORACLE_LAYERS",
    "VALID_CATEGORIES",
    "graph_node_by_key",
    "has_business_oracle",
    "node_category",
]
