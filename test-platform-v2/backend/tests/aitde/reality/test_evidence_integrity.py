"""V3.9-R1 TRUST-004 / TRUST-005 — Evidence physical integrity + snapshot sanitizer.

Verifies that a 0-byte / empty-hash / missing-object artifact can never satisfy a
Required Evidence (the Real-Gate red-team target) and that an ExecutionStep
snapshot never carries raw Authorization / Cookie / token / password.
"""
from __future__ import annotations

from app.modules.aitde.assertion.completeness import (
    artifact_usable,
    is_complete_artifacts,
    required_evidence,
)
from app.modules.aitde.evidence.snapshot_sanitizer import snapshot_sanitizer
from app.modules.aitde.execution.models import EvidenceArtifact


def _artifact(**overrides) -> EvidenceArtifact:
    base = {
        "project_id": 1,
        "run_id": 1,
        "evidence_type": "REQUEST",
        "storage_provider": "local",
        "storage_uri": "/project/1/mission/0/run/1/evidence-request",
        "content_hash": "a" * 64,
        "content_type": "application/json",
        "size_bytes": 128,
        "sanitization_status": "SANITIZED",
        "integrity_status": "VERIFIED",
    }
    base.update(overrides)
    return EvidenceArtifact(**base)


# ── completeness.artifact_usable ─────────────────────────────────────────────


def test_artifact_usable_rejects_empty_storage_uri() -> None:
    assert artifact_usable(_artifact(storage_uri="")) is False


def test_artifact_usable_rejects_short_hash() -> None:
    assert artifact_usable(_artifact(content_hash="abc")) is False


def test_artifact_usable_rejects_zero_bytes() -> None:
    assert artifact_usable(_artifact(size_bytes=0)) is False


def test_artifact_usable_rejects_not_sanitized() -> None:
    assert artifact_usable(_artifact(sanitization_status="PENDING")) is False


def test_artifact_usable_rejects_not_verified_integrity() -> None:
    assert artifact_usable(_artifact(integrity_status="PENDING")) is False


def test_artifact_usable_accepts_valid_artifact() -> None:
    assert artifact_usable(_artifact()) is True


# ── completeness.is_complete_artifacts ───────────────────────────────────────


def test_is_complete_artifacts_requires_usable_per_type() -> None:
    required = ["REQUEST", "RESPONSE"]
    # A fake REQUEST (0-byte) must not satisfy the required set.
    fake = _artifact(evidence_type="REQUEST", size_bytes=0)
    ok = _artifact(evidence_type="RESPONSE")
    assert is_complete_artifacts([fake, ok], required) is False

    valid_req = _artifact(evidence_type="REQUEST")
    assert is_complete_artifacts([valid_req, ok], required) is True


def test_is_complete_artifacts_supports_min_count() -> None:
    artifacts = [_artifact(evidence_type="SCREENSHOT", id=1), _artifact(evidence_type="SCREENSHOT", id=2)]
    assert is_complete_artifacts(artifacts, ["SCREENSHOT"], required_counts={"SCREENSHOT": 2}) is True
    assert is_complete_artifacts(artifacts, ["SCREENSHOT"], required_counts={"SCREENSHOT": 3}) is False


def test_required_evidence_api_pair_unchanged() -> None:
    assert set(required_evidence("API", "API")) == {"REQUEST", "RESPONSE"}


# ── snapshot_sanitizer (TRUST-005) ───────────────────────────────────────────


def test_snapshot_sanitizer_redacts_http_headers() -> None:
    snap = snapshot_sanitizer.sanitize_http_snapshot(
        method="POST",
        url="http://svc/renew",
        headers={"Authorization": "Bearer secret", "Cookie": "session=1", "X-Trace": "ok"},
        params={"a": "1"},
        body={"token": "abc", "name": "alice"},
    )
    assert snap["headers"]["Authorization"] == "<REDACTED>"
    assert snap["headers"]["Cookie"] == "<REDACTED>"
    assert snap["headers"]["X-Trace"] == "ok"
    assert snap["body"]["token"] == "<REDACTED>"
    assert snap["body"]["name"] == "alice"


def test_snapshot_sanitizer_redacts_nested_sensitive_keys() -> None:
    value = {"data": {"password": "hunter2", "access_token": "t", "profile": {"email": "a@b.c"}}}
    out = snapshot_sanitizer.sanitize_snapshot(value)
    assert out["data"]["password"] == "<REDACTED>"
    assert out["data"]["access_token"] == "<REDACTED>"
    assert out["data"]["profile"]["email"] == "a@b.c"


def test_snapshot_sanitizer_bearer_in_plain_text() -> None:
    text = snapshot_sanitizer.sanitize_snapshot("Authorization: Bearer eyJhbGciOiJ")
    assert "Bearer eyJhbGciOiJ" not in text


def test_snapshot_sanitizer_preserves_normal_values() -> None:
    value = {"status": 200, "name": "alice", "items": [1, 2, 3]}
    out = snapshot_sanitizer.sanitize_snapshot(value)
    assert out == value


def test_snapshot_sanitizer_dump_serializes() -> None:
    dumped = snapshot_sanitizer.dump({"token": "x", "status": 200})
    assert "x" not in dumped
    assert '"status": 200' in dumped
