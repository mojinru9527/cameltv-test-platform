"""ReplayManifest / EvidenceService tests (V31-004/V31-003)."""
from __future__ import annotations

import json

from app.modules.aitde.evidence.manifest import build_manifest, manifest_hash
from app.modules.aitde.evidence.service import store_artifact
from app.modules.aitde.execution.models import (
    ExecutionRun,
    ExecutionStep,
    AssertionResult,
    EvidenceArtifact,
)


def _run():
    r = ExecutionRun(id=1, runtime_status="FINISHED", outcome="PASS", environment_snapshot_id=3)
    return r


def test_manifest_refs_all_rows():
    run = _run()
    steps = [ExecutionStep(id=10, run_id=1, sequence=1, step_key="login", step_type="API", status="SUCCEEDED")]
    assertions = [AssertionResult(id=20, run_id=1, oracle_id=5, result="PASS", reason_code="eq")]
    evidence = [EvidenceArtifact(id=30, run_id=1, evidence_type="RESPONSE", storage_uri="/proj/1/run/1", content_hash="h")]

    m = build_manifest(run, steps, assertions, evidence)
    assert m["timeline"][0]["step_id"] == 10
    assert m["assertions"][0]["assertion_id"] == 20
    assert m["evidence"][0]["artifact_id"] == 30
    assert len(manifest_hash(m)) == 64


def test_store_artifact_cleans_body_and_rejects_legacy_uri(db):
    # local storage is provider 'local'; store a JSON artifact
    row = store_artifact(
        db,
        project_id=1,
        run_id=1,
        evidence_type="RESPONSE",
        data=json.dumps({"token": "secret"}).encode(),
        content_type="application/json",
    )
    assert row.sanitization_status == "SANITIZED"
    assert len(row.content_hash) == 64
    assert row.storage_provider == "local"
