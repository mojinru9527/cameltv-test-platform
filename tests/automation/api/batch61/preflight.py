from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Any


REQUIRED_SERVICES = frozenset({"camel", "live", "payment", "studio", "konfi", "account"})
REQUIRED_STABLE_RECORDS = frozenset(
    {
        "normal_user",
        "low_balance_user",
        "first_purchase_user",
        "used_eligibility_user",
        "recommended_author",
        "yield_order",
        "category",
        "pinned_article",
        "free_article",
        "paid_article",
        "locked_prediction",
        "unlocked_prediction",
        "settled_win_prediction",
        "settled_loss_prediction",
        "bonus_package",
        "non_bonus_package",
        "readonly_order",
        "readonly_operations_account",
    }
)
SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "passwd",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "private_key",
        "client_secret",
        "credential",
        "credentials",
        "secret",
        "secrets",
    }
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"^(?:Bearer|Basic)\s+\S+", re.IGNORECASE),
    re.compile(r"^AKIA[0-9A-Z]{16}$"),
    re.compile(r"^(?:sk|ghp|github_pat)-?_[A-Za-z0-9_-]{16,}$", re.IGNORECASE),
    re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"),
)
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
GIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")
SECRET_REFERENCE_PATTERN = re.compile(r"^secret://[A-Za-z0-9][A-Za-z0-9._/-]*$")


class BlockedPrerequisite(RuntimeError):
    def __init__(self, key: str, owner: str) -> None:
        self.key = key
        self.owner = owner
        self.status = "BLOCKED"
        super().__init__(f"B61-BLOCKED:{key}")


@dataclass(frozen=True, slots=True)
class ValidatedManifest:
    environment: str
    owner: str
    services: tuple[str, ...]
    allowed_methods: tuple[str, ...]
    contract_hashes: tuple[tuple[str, str], ...]
    code_shas: tuple[tuple[str, str], ...]


def _owner(manifest: Mapping[str, Any]) -> str:
    owner = manifest.get("owner")
    return owner.strip() if isinstance(owner, str) and owner.strip() else "UNASSIGNED"


def _block(owner: str, key: str) -> None:
    raise BlockedPrerequisite(key, owner)


def _mapping(value: Any, owner: str, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _block(owner, key)
    return value


def _nonempty_string(value: Any, owner: str, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _block(owner, key)
    return value.strip()


def _positive_int(value: Any, owner: str, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        _block(owner, key)
    return value


def _aware_datetime(value: Any, owner: str, key: str) -> datetime:
    raw = _nonempty_string(value, owner, key)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _block(owner, key)
    if parsed.tzinfo is None:
        _block(owner, key)
    return parsed


def _vpn_window(value: Any, owner: str) -> tuple[datetime, datetime]:
    window = _nonempty_string(value, owner, "vpn.window")
    parts = window.split("/")
    if len(parts) != 2:
        _block(owner, "vpn.window")
    starts_at = _aware_datetime(parts[0], owner, "vpn.window")
    end_value = parts[1]
    if "T" not in end_value:
        end_value = f"{starts_at.date().isoformat()}T{end_value}"
    ends_at = _aware_datetime(end_value, owner, "vpn.window")
    if ends_at <= starts_at and "T" not in parts[1]:
        ends_at += timedelta(days=1)
    if starts_at >= ends_at:
        _block(owner, "vpn.window")
    return starts_at, ends_at


def _reject_sensitive_data(value: Any, owner: str, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key)
            normalized = key.strip().lower().replace("-", "_")
            current_path = (*path, key)
            if normalized != "secret_reference" and normalized in SENSITIVE_FIELD_NAMES:
                _block(owner, f"SENSITIVE_FIELD:{'.'.join(current_path)}")
            _reject_sensitive_data(nested, owner, current_path)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _reject_sensitive_data(nested, owner, (*path, str(index)))
        return
    if isinstance(value, str) and any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
        _block(owner, f"SENSITIVE_VALUE:{'.'.join(path)}")


def validate_manifest(manifest: Mapping[str, Any]) -> ValidatedManifest:
    if not isinstance(manifest, Mapping):
        raise BlockedPrerequisite("manifest", "UNASSIGNED")

    owner = _owner(manifest)
    if owner == "UNASSIGNED":
        _block(owner, "owner")
    _reject_sensitive_data(manifest, owner)

    environment = _nonempty_string(manifest.get("environment"), owner, "environment").lower()
    if environment not in {"test5", "production"}:
        _block(owner, "environment")

    vpn = _mapping(manifest.get("vpn"), owner, "vpn")
    if vpn.get("authorized") is not True:
        _block(owner, "vpn.authorized")
    _vpn_window(vpn.get("window"), owner)

    contracts = _mapping(manifest.get("contracts"), owner, "contracts")
    contract_hashes: list[tuple[str, str]] = []
    for service in sorted(REQUIRED_SERVICES):
        contract = _mapping(contracts.get(service), owner, f"contracts.{service}")
        digest = _nonempty_string(contract.get("sha256"), owner, f"contracts.{service}.sha256")
        if not SHA256_PATTERN.fullmatch(digest):
            _block(owner, f"contracts.{service}.sha256")
        _aware_datetime(contract.get("exported_at"), owner, f"contracts.{service}.exported_at")
        _nonempty_string(contract.get("version"), owner, f"contracts.{service}.version")
        route = _nonempty_string(contract.get("gateway_route"), owner, f"contracts.{service}.gateway_route")
        if not route.startswith("/") or route.startswith("//"):
            _block(owner, f"contracts.{service}.gateway_route")
        contract_hashes.append((service, digest.lower()))

    account = _mapping(manifest.get("account"), owner, "account")
    secret_reference = _nonempty_string(account.get("secret_reference"), owner, "account.secret_reference")
    if not SECRET_REFERENCE_PATTERN.fullmatch(secret_reference):
        _block(owner, "account.secret_reference")
    if _nonempty_string(account.get("scope"), owner, "account.scope").lower() != "readonly":
        _block(owner, "account.scope")
    _aware_datetime(account.get("expires_at"), owner, "account.expires_at")
    _nonempty_string(account.get("revoke_owner"), owner, "account.revoke_owner")

    stable_records = _mapping(manifest.get("stable_records"), owner, "stable_records")
    for record_key in sorted(REQUIRED_STABLE_RECORDS):
        _nonempty_string(stable_records.get(record_key), owner, f"stable_records.{record_key}")

    rate_limit = _mapping(manifest.get("rate_limit"), owner, "rate_limit")
    _positive_int(rate_limit.get("requests"), owner, "rate_limit.requests")
    _positive_int(rate_limit.get("window_seconds"), owner, "rate_limit.window_seconds")

    evidence = _mapping(manifest.get("evidence"), owner, "evidence")
    _positive_int(evidence.get("retention_days"), owner, "evidence.retention_days")
    _nonempty_string(evidence.get("cleanup_owner"), owner, "evidence.cleanup_owner")
    _nonempty_string(evidence.get("cleanup_rule"), owner, "evidence.cleanup_rule")

    methods = manifest.get("allowed_methods")
    if not isinstance(methods, Sequence) or isinstance(methods, (str, bytes, bytearray)) or not methods:
        _block(owner, "allowed_methods")
    normalized_methods = tuple(sorted({_nonempty_string(method, owner, "allowed_methods").upper() for method in methods}))
    if environment == "production" and any(method not in {"GET", "HEAD"} for method in normalized_methods):
        _block(owner, "PRODUCTION_WRITE_METHOD")

    code_shas = _mapping(manifest.get("code_shas"), owner, "code_shas")
    normalized_code_shas: list[tuple[str, str]] = []
    for component in ("frontend", "backend", "services"):
        sha = _nonempty_string(code_shas.get(component), owner, f"code_shas.{component}")
        if not GIT_SHA_PATTERN.fullmatch(sha):
            _block(owner, f"code_shas.{component}")
        normalized_code_shas.append((component, sha.lower()))

    return ValidatedManifest(
        environment=environment,
        owner=owner,
        services=tuple(sorted(REQUIRED_SERVICES)),
        allowed_methods=normalized_methods,
        contract_hashes=tuple(contract_hashes),
        code_shas=tuple(normalized_code_shas),
    )
