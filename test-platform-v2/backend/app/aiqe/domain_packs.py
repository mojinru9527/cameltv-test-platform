"""M8 / TA-043/044/045：Domain Packs（E-commerce / SaaS / IoT）。"""
from __future__ import annotations

from dataclasses import dataclass


class DomainPackError(ValueError):
    pass


@dataclass(frozen=True)
class DomainPack:
    key: str
    name: str
    roles: tuple[str, ...]
    entities: tuple[str, ...]
    checks: tuple[str, ...]
    capabilities: tuple[str, ...] = ()


PACKS: dict[str, DomainPack] = {
    "ecommerce": DomainPack(
        key="ecommerce",
        name="E-commerce（future-wayu）",
        roles=("buyer", "seller", "admin"),
        entities=("product", "cart", "order", "refund"),
        checks=("payment_success", "refund_flow", "inventory_consistency"),
        capabilities=("api.http", "browser.chromium"),
    ),
    "saas": DomainPack(
        key="saas",
        name="SaaS（Tenant/RBAC/Audit）",
        roles=("owner", "admin", "member", "guest"),
        entities=("tenant", "workspace", "role", "audit_log"),
        checks=("tenant_isolation", "rbac_enforcement", "audit_trail"),
        capabilities=("api.http",),
    ),
    "iot": DomainPack(
        key="iot",
        name="IoT（Device shadow / telemetry）",
        roles=("operator", "viewer"),
        entities=("device", "device_shadow", "telemetry", "alert"),
        checks=("shadow_sync", "telemetry_freshness", "alert_delivery"),
        capabilities=("db.readonly", "api.http"),
    ),
}

REQUIRED_CHECKS: dict[str, tuple[str, ...]] = {
    "ecommerce": ("payment_success", "refund_flow"),
    "saas": ("tenant_isolation", "rbac_enforcement", "audit_trail"),
    "iot": ("shadow_sync", "telemetry_freshness"),
}


def list_packs() -> list[str]:
    return sorted(PACKS)


def get_pack(key: str) -> DomainPack:
    pack = PACKS.get(str(key).lower())
    if pack is None:
        raise DomainPackError(f"未知 Domain Pack: {key}")
    return pack


def validate_pack(pack: DomainPack) -> dict:
    if not pack.roles or not pack.entities or not pack.checks:
        raise DomainPackError(f"{pack.key} 缺少 roles/entities/checks")
    missing = [check for check in REQUIRED_CHECKS.get(pack.key, ()) if check not in pack.checks]
    if missing:
        raise DomainPackError(f"{pack.key} 缺少必备检查: {missing}")
    return {"key": pack.key, "valid": True, "checks": len(pack.checks)}


def apply_pack(key: str) -> dict:
    pack = get_pack(key)
    return {
        "pack": pack.key,
        "name": pack.name,
        "roles": list(pack.roles),
        "entities": list(pack.entities),
        "checks": list(pack.checks),
        "capabilities": list(pack.capabilities),
        "validation": validate_pack(pack),
    }
