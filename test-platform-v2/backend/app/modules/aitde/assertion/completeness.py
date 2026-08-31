"""EvidenceCompletenessPolicy (V31-004 / V31-010 / V3.9-R1 TRUST-004).

Defines the *required* evidence set for an (adapter_type, oracle_type) pair. A
Run can only be a PASS when every required oracle evaluates and the required
evidence is complete. Missing required evidence degrades PASS -> INCONCLUSIVE.

V3.9-R1 hardening: completeness is no longer "does an artifact row of the right
type exist". A required evidence is COMPLETE only when the artifact is physically
usable — sanitized, hash-valid, non-empty, and confirmed present in object
storage. A 0-byte / empty-hash / storage-missing artifact must never satisfy a
Required Evidence (the Real-Gate red-team target).
"""
from __future__ import annotations

import re
from typing import Any

from app.modules.aitde.common.enums import AdapterType, EvidenceType, OracleType

# Default evidence a PASS needs, keyed by (adapter_type, oracle_type).
_DEFAULT_REQUIRED: dict[tuple[str, str], list[str]] = {
    (AdapterType.API.value, OracleType.API.value): [
        EvidenceType.REQUEST.value, EvidenceType.RESPONSE.value,
    ],
    (AdapterType.UI.value, OracleType.UI.value): [
        EvidenceType.SCREENSHOT.value, EvidenceType.CONSOLE.value,
    ],
    (AdapterType.UI.value, OracleType.API.value): [
        EvidenceType.RESPONSE.value, EvidenceType.SCREENSHOT.value,
    ],
    (AdapterType.MANUAL.value, OracleType.UI.value): [
        EvidenceType.SCREENSHOT.value,
    ],
    (AdapterType.MANUAL.value, OracleType.API.value): [
        EvidenceType.RESPONSE.value,
    ],
}

_FALLBACK_REQUIRED: list[str] = [
    EvidenceType.RESPONSE.value, EvidenceType.SCREENSHOT.value,
]

# A valid sha256 hex digest (64 hex chars).
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# Trusted integrity statuses that may satisfy a Required Evidence.
_TRUSTED_INTEGRITY = {"VERIFIED"}


def required_evidence(adapter_type: str, oracle_type: str) -> list[str]:
    """Return the required evidence type strings for an (adapter, oracle) pair."""
    return list(_DEFAULT_REQUIRED.get((adapter_type, oracle_type), _FALLBACK_REQUIRED))


def is_complete(present_types: set[str], required_types: list[str]) -> bool:
    """True only when every required evidence type is present.

    Legacy presence-only check; retained for backward compatibility. New runtime
    should prefer :func:`is_complete_artifacts` so physical integrity is enforced.
    """
    return all(rt in present_types for rt in required_types)


def artifact_usable(artifact: Any) -> bool:
    """True when a single EvidenceArtifact is physically usable as proof.

    A Requred Evidence may only be satisfied by an artifact that is sanitized,
    hash-valid, non-empty, and confirmed present in object storage. This is the
    V3.9-R1 (TRUST-004) integrity threshold; a 0-byte / empty-hash / missing-object
    artifact is never usable.
    """
    if artifact is None:
        return False
    storage_uri = getattr(artifact, "storage_uri", None) or ""
    content_hash = getattr(artifact, "content_hash", None) or ""
    size_bytes = getattr(artifact, "size_bytes", 0) or 0
    sanitization_status = getattr(artifact, "sanitization_status", "") or ""
    integrity_status = getattr(artifact, "integrity_status", "") or ""

    if not storage_uri:
        return False
    if not _SHA256_RE.match(content_hash):
        return False
    if size_bytes <= 0:
        return False
    if str(sanitization_status).upper() != "SANITIZED":
        return False
    # VERIFIED means the object store HEAD confirmed presence/size/hash.
    return str(integrity_status).upper() in _TRUSTED_INTEGRITY


def _artifact_type(artifact: Any) -> str:
    return str(getattr(artifact, "evidence_type", "") or "")


def is_complete_artifacts(
    artifacts: list[Any] | None,
    required_types: list[str] | None,
    *,
    required_counts: dict[str, int] | None = None,
) -> bool:
    """True only when every required evidence type has enough *usable* artifacts.

    Each required type is satisfied only by artifacts that pass the physical
    integrity threshold (:func:`artifact_usable`). ``required_counts`` optionally
    raises the count (e.g. MIN_COUNT), defaulting to 1 per type. Because a
    missing / 0-byte / hash-less artifact never counts, a fake row can no longer
    satisfy a Required Evidence.
    """
    required_types = required_types or []
    artifacts = artifacts or []
    if not required_types:
        return True

    by_type: dict[str, list[Any]] = {}
    for artifact in artifacts:
        atype = _artifact_type(artifact)
        if artifact_usable(artifact):
            by_type.setdefault(atype, []).append(artifact)

    for req_type in required_types:
        need = (required_counts or {}).get(req_type, 1)
        if len(by_type.get(req_type, [])) < need:
            return False
    return True
