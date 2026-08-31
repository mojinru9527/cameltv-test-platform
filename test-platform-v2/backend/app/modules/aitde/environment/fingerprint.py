"""Environment fingerprint (V31-001) + V3.9-R3 (FINGER-001) real probes.

``compute_fingerprint_hash`` remains the stable hashing core. V3.9-R3 adds a
*probe* layer so the fingerprint is *observed* (HTTP version, OpenAPI hash, DB
migration, static asset, response header) rather than only caller-supplied, and
carries a ``confidence`` so a Quality Gate can require HIGH/MEDIUM confidence
before a Release Gate (plan §57).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol


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


# ── V3.9-R3 (FINGER-001) probe layer ────────────────────────────────────────


# Non-secret observed factors that raise confidence when present in a fingerprint.
_OBSERVED_FACTORS = (
    "service_versions",
    "openapi_hash",
    "db_schema_version",
    "config_hash",
    "static_asset_hash",
    "frontend_version",
)


def confidence_from_components(components: dict[str, Any] | None) -> str:
    """Map how many real environment factors a fingerprint carries to a level.

    Deterministic and credential-free: 3+ observed factors -> HIGH, 1-2 -> MEDIUM,
    none (e.g. only a manual build_label) -> LOW. A LOW-confidence fingerprint
    must not satisfy a P0 release gate that requires MEDIUM/HIGH (plan §57).
    """
    components = components or {}
    present = sum(1 for k in _OBSERVED_FACTORS if components.get(k))
    if present >= 3:
        return "HIGH"
    if present >= 1:
        return "MEDIUM"
    return "LOW"


@dataclass
class ProbeResult:
    key: str
    value: Any
    observed: bool = False
    confidence: float = 0.0


class FingerprintProbe(Protocol):
    key: str

    def capture(self, context: dict[str, Any]) -> ProbeResult: ...


class ManualBuildLabelProbe:
    """Low-confidence: a manually-listed build label is evidence but not observed."""

    key = "build_label"

    def capture(self, context: dict[str, Any]) -> ProbeResult:
        label = context.get("build_label")
        return ProbeResult(self.key, label or "", observed=bool(label), confidence=0.3 if label else 0.0)


class HttpVersionProbe:
    """Observed service versions via an HTTP /version endpoint (best-effort)."""

    key = "service_versions"

    def capture(self, context: dict[str, Any]) -> ProbeResult:
        url = context.get("version_url")
        if not url:
            return ProbeResult(self.key, {}, observed=False, confidence=0.0)
        try:
            import httpx

            resp = httpx.get(url, timeout=5, verify=True)
            resp.raise_for_status()
            data = resp.json()
            versions = data if isinstance(data, dict) else {"version": str(data)}
            return ProbeResult(self.key, versions, observed=True, confidence=0.9)
        except Exception:  # noqa: BLE001 — a failed probe is NOT an observation
            return ProbeResult(self.key, {}, observed=False, confidence=0.0)


class OpenApiHashProbe:
    """Observed OpenAPI doc hash via an HTTP GET of the live /openapi.json."""

    key = "openapi_hash"

    def capture(self, context: dict[str, Any]) -> ProbeResult:
        url = context.get("openapi_url")
        if not url:
            return ProbeResult(self.key, "", observed=False, confidence=0.0)
        try:
            import httpx

            resp = httpx.get(url, timeout=5, verify=True)
            resp.raise_for_status()
            digest = hashlib.sha256(resp.content).hexdigest()
            return ProbeResult(self.key, digest, observed=True, confidence=0.9)
        except Exception:  # noqa: BLE001
            return ProbeResult(self.key, "", observed=False, confidence=0.0)


class DbMigrationProbe:
    """Observed DB schema version (read-only) — value supplied by the caller's
    read-only path, marked as observed only when a DB version string is present."""

    key = "db_schema_version"

    def capture(self, context: dict[str, Any]) -> ProbeResult:
        value = context.get("db_schema_version")
        return ProbeResult(self.key, value or "", observed=bool(value), confidence=0.6 if value else 0.0)


class StaticAssetProbe:
    """Observed static asset hash (frontend build)."""

    key = "static_asset_hash"

    def capture(self, context: dict[str, Any]) -> ProbeResult:
        value = context.get("static_asset_hash")
        return ProbeResult(self.key, value or "", observed=bool(value), confidence=0.7 if value else 0.0)


class ResponseHeaderProbe:
    """Observed response header (e.g. a build/version header)."""

    key = "response_header"

    def capture(self, context: dict[str, Any]) -> ProbeResult:
        value = context.get("response_header")
        return ProbeResult(self.key, value or "", observed=bool(value), confidence=0.8 if value else 0.0)


# Registry order determines probe precedence for the same fingerprint slot.
_PROBES: list[FingerprintProbe] = [
    ManualBuildLabelProbe(),
    HttpVersionProbe(),
    OpenApiHashProbe(),
    DbMigrationProbe(),
    StaticAssetProbe(),
    ResponseHeaderProbe(),
]


def probe_environment(context: dict[str, Any]) -> dict[str, Any]:
    """Run all probes and assemble an observed fingerprint + confidence.

    Returns ``{"components": {...}, "confidence": <LOW|MEDIUM|HIGH>, "probes": [...]}``.
    A fingerprint assembled only from a manual build_label is LOW confidence and
    must not satisfy a P0 release gate that requires MEDIUM/HIGH (plan §57).
    """
    results: dict[str, Any] = {}
    probe_meta: list[dict[str, Any]] = []
    confidences: list[float] = []
    for probe in _PROBES:
        try:
            r = probe.capture(context)
        except Exception:  # noqa: BLE001 — a probe crash is not an observation
            r = ProbeResult(probe.key, None, observed=False, confidence=0.0)
        results[r.key] = r.value
        probe_meta.append({"probe": probe.key, "observed": r.observed, "confidence": r.confidence})
        if r.confidence > 0.0:
            confidences.append(r.confidence)

    # Confidence = average of observed probes; LOW when nothing observed.
    if not confidences:
        level = "LOW"
    else:
        avg = sum(confidences) / len(confidences)
        level = "HIGH" if avg >= 0.8 else ("MEDIUM" if avg >= 0.5 else "LOW")
    return {"components": results, "confidence": level, "probes": probe_meta}
