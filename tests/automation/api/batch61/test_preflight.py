import pytest
from dataclasses import FrozenInstanceError

from tests.automation.api.batch61.preflight import (
    BlockedPrerequisite,
    validate_manifest,
)


def valid_test5_manifest() -> dict:
    contract_hashes = {
        "camel": "a" * 64,
        "live": "b" * 64,
        "payment": "c" * 64,
        "studio": "d" * 64,
        "konfi": "e" * 64,
        "account": "f" * 64,
    }
    contracts = {
        service: {
            "sha256": contract_hashes[service],
            "exported_at": "2026-08-01T00:00:00Z",
            "version": "batch61-current",
            "gateway_route": f"/{service}-service",
        }
        for service in ("camel", "live", "payment", "studio", "konfi", "account")
    }
    return {
        "environment": "test5",
        "owner": "sports-qa",
        "vpn": {"authorized": True, "window": "2026-08-02T01:00:00Z/02:00:00Z"},
        "contracts": contracts,
        "account": {
            "secret_reference": "secret://test5/sports-readonly",
            "scope": "readonly",
            "expires_at": "2026-08-03T00:00:00Z",
            "revoke_owner": "account-owner",
        },
        "stable_records": {
            "normal_user": "user-normal-001",
            "low_balance_user": "user-low-balance-001",
            "first_purchase_user": "user-first-purchase-001",
            "used_eligibility_user": "user-used-eligibility-001",
            "recommended_author": "author-yield-001",
            "yield_order": "order-yield-001",
            "category": "category-football-001",
            "pinned_article": "article-pinned-001",
            "free_article": "article-free-001",
            "paid_article": "article-paid-001",
            "locked_prediction": "prediction-locked-001",
            "unlocked_prediction": "prediction-unlocked-001",
            "settled_win_prediction": "prediction-win-001",
            "settled_loss_prediction": "prediction-loss-001",
            "bonus_package": "package-bonus-001",
            "non_bonus_package": "package-standard-001",
            "readonly_order": "order-readonly-001",
            "readonly_operations_account": "operations-readonly-001",
        },
        "rate_limit": {"requests": 30, "window_seconds": 60},
        "evidence": {
            "retention_days": 30,
            "cleanup_owner": "sports-qa",
            "cleanup_rule": "delete Batch 61 write fixtures after reconciliation",
        },
        "allowed_methods": ["GET", "HEAD"],
        "code_shas": {
            "frontend": "1" * 40,
            "backend": "2" * 40,
            "services": "3" * 40,
        },
    }


def test_missing_vpn_authorization_is_structured_blocked() -> None:
    manifest = valid_test5_manifest()
    manifest["vpn"]["authorized"] = False

    with pytest.raises(BlockedPrerequisite, match="B61-BLOCKED:vpn.authorized") as exc:
        validate_manifest(manifest)

    assert exc.value.owner == "sports-qa"
    assert exc.value.status == "BLOCKED"


def test_all_six_current_contracts_are_required() -> None:
    manifest = valid_test5_manifest()
    del manifest["contracts"]["payment"]

    with pytest.raises(BlockedPrerequisite, match="contracts.payment"):
        validate_manifest(manifest)


def test_production_is_get_head_only() -> None:
    manifest = valid_test5_manifest()
    manifest["environment"] = "production"
    manifest["allowed_methods"] = ["GET", "POST"]

    with pytest.raises(BlockedPrerequisite, match="PRODUCTION_WRITE_METHOD"):
        validate_manifest(manifest)


def test_secret_values_are_forbidden_even_under_nested_fields() -> None:
    manifest = valid_test5_manifest()
    manifest["account"]["access_token"] = "raw-secret"

    with pytest.raises(BlockedPrerequisite, match="SENSITIVE_FIELD"):
        validate_manifest(manifest)


def test_complete_readonly_manifest_passes_without_network_activity() -> None:
    result = validate_manifest(valid_test5_manifest())

    assert result.environment == "test5"
    assert result.services == ("account", "camel", "konfi", "live", "payment", "studio")
    assert result.allowed_methods == ("GET", "HEAD")


@pytest.mark.parametrize(
    ("path", "value", "blocked_key"),
    [
        (("contracts", "camel", "sha256"), "not-a-sha", "contracts.camel.sha256"),
        (("contracts", "live", "exported_at"), "yesterday", "contracts.live.exported_at"),
        (("contracts", "payment", "version"), "", "contracts.payment.version"),
        (("contracts", "studio", "gateway_route"), "https://service", "contracts.studio.gateway_route"),
        (("account", "secret_reference"), "plain-token", "account.secret_reference"),
        (("account", "scope"), "admin", "account.scope"),
        (("rate_limit", "requests"), 0, "rate_limit.requests"),
        (("code_shas", "frontend"), "short", "code_shas.frontend"),
        (("evidence", "retention_days"), 0, "evidence.retention_days"),
    ],
)
def test_invalid_prerequisites_are_structured_blocked(
    path: tuple[str, ...], value: object, blocked_key: str
) -> None:
    manifest = valid_test5_manifest()
    target = manifest
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(BlockedPrerequisite, match=blocked_key.replace(".", r"\.")):
        validate_manifest(manifest)


def test_all_required_stable_records_are_required() -> None:
    manifest = valid_test5_manifest()
    del manifest["stable_records"]["locked_prediction"]

    with pytest.raises(BlockedPrerequisite, match="stable_records.locked_prediction"):
        validate_manifest(manifest)


def test_result_is_immutable_and_normalized() -> None:
    manifest = valid_test5_manifest()
    manifest["allowed_methods"] = ["head", "GET", "get"]

    result = validate_manifest(manifest)

    assert result.allowed_methods == ("GET", "HEAD")
    with pytest.raises(FrozenInstanceError):
        result.environment = "production"
