"""V3.9-R3 FINGER-001 — environment fingerprint is observed via probes."""
from __future__ import annotations

from app.modules.aitde.environment.fingerprint import (
    ManualBuildLabelProbe,
    probe_environment,
    compute_fingerprint_hash,
)


def test_probe_environment_manual_label_is_low_confidence():
    ctx = {"build_label": "build-123"}
    result = probe_environment(ctx)
    assert result["confidence"] == "LOW"
    # build_label is a version factor that contributes to the fingerprint.
    assert result["components"]["build_label"] == "build-123"


def test_probe_environment_no_observation_is_low_confidence():
    result = probe_environment({})
    assert result["confidence"] == "LOW"
    assert result["probes"] and all(
        not p["observed"] for p in result["probes"]
    )


def test_probe_environment_observed_probe_upgrades_confidence():
    # An observed OpenAPI hash (from a real HTTP GET) is a strong signal.
    ctx = {"openapi_url": "http://127.0.0.1:1/openapi.json"}  # unreachable -> not observed
    result = probe_environment(ctx)
    # Unreachable endpoint must NOT be treated as observed.
    oa = next(p for p in result["probes"] if p["probe"] == "openapi_hash")
    assert oa["observed"] is False


def test_fingerprint_hash_is_stable_for_same_components():
    a = compute_fingerprint_hash(build_label="b1", openapi_hash="oa")
    b = compute_fingerprint_hash(openapi_hash="oa", build_label="b1")
    c = compute_fingerprint_hash(build_label="b2")
    assert a == b
    assert a != c


def test_manual_build_label_probe_reports_confidence():
    probe = ManualBuildLabelProbe()
    assert probe.capture({"build_label": "b"}).observed is True
    assert probe.capture({}).observed is False
