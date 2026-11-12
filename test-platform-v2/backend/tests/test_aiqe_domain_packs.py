"""M8 / TA-043/044/045：Domain Packs 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.domain_packs import (
    DomainPack,
    DomainPackError,
    apply_pack,
    get_pack,
    list_packs,
    validate_pack,
)


def test_three_packs_registered():
    assert list_packs() == ["ecommerce", "iot", "saas"]


def test_get_pack_and_unknown():
    assert get_pack("ecommerce").name.startswith("E-commerce")
    with pytest.raises(DomainPackError):
        get_pack("crypto")


def test_all_packs_valid():
    for key in list_packs():
        assert validate_pack(get_pack(key))["valid"] is True


def test_saas_requires_tenant_rbac_audit():
    checks = get_pack("saas").checks
    assert {"tenant_isolation", "rbac_enforcement", "audit_trail"} <= set(checks)


def test_iot_shadow_and_telemetry():
    checks = get_pack("iot").checks
    assert "shadow_sync" in checks and "telemetry_freshness" in checks


def test_apply_pack_shape():
    result = apply_pack("ecommerce")
    assert result["pack"] == "ecommerce"
    assert result["validation"]["valid"] is True
    assert "payment_success" in result["checks"]


def test_missing_checks_rejected():
    broken = DomainPack(
        key="ecommerce",
        name="broken",
        roles=("buyer",),
        entities=("order",),
        checks=("inventory_consistency",),
    )
    with pytest.raises(DomainPackError):
        validate_pack(broken)
