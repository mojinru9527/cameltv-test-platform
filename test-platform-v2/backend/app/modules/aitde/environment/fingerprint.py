"""Environment fingerprint (V31-001).

Computes a deterministic, stable hash over the captured environment factors that
matter for reproducibility. ``fingerprint_hash`` binds a Run to a specific
environment without storing secrets: we only hash stable identifiers + labels.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json(data: dict[str, Any]) -> str:
    """Canonical JSON (sorted keys, compact separators) so the hash never depends
    on dict insertion order."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_fingerprint_hash(
    service_versions: dict[str, str] | None = None,
    openapi_hash: str | None = None,
    db_schema_version: str | None = None,
    config_hash: str | None = None,
    static_asset_hash: str | None = None,
    frontend_version: str | None = None,
    build_label: str | None = None,
) -> str:
    """sha256 over the stable, non-secret environment identity factors."""
    payload = {
        "sv": stable_json(service_versions or {}),
        "oa": openapi_hash or "",
        "db": db_schema_version or "",
        "cfg": config_hash or "",
        "static": static_asset_hash or "",
        "fe": frontend_version or "",
        "build": build_label or "",
    }
    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
