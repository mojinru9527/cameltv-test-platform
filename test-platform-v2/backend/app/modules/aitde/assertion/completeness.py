"""EvidenceCompletenessPolicy (V31-004 / V31-010).

Defines the *required* evidence set for an (adapter_type, oracle_type) pair. A
Run can only be a PASS when every required oracle evaluates and the required
evidence is complete. Missing required evidence degrades PASS -> INCONCLUSIVE.
"""
from __future__ import annotations

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


def required_evidence(adapter_type: str, oracle_type: str) -> list[str]:
    """Return the required evidence type strings for an (adapter, oracle) pair."""
    return list(_DEFAULT_REQUIRED.get((adapter_type, oracle_type), _FALLBACK_REQUIRED))


def is_complete(present_types: set[str], required_types: list[str]) -> bool:
    """True only when every required evidence type is present (and sanitized)."""
    return all(rt in present_types for rt in required_types)
