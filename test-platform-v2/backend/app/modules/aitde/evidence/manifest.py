"""Replay manifest builder (V31-004).

An append-only ``ReplayManifest`` references every step, oracle assertion and
evidence artifact for a run so a proof replay can be reconstructed post-hoc. All
``manifest`` refs must resolve to real steps/assertions/evidence.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from app.modules.aitde.execution.models import (
    AssertionResult,
    EvidenceArtifact,
    ExecutionRun,
    ExecutionStep,
)


def build_manifest(
    run: ExecutionRun,
    steps: list[ExecutionStep],
    assertions: list[AssertionResult],
    evidence: list[EvidenceArtifact],
    schema_version: str = "1.0",
) -> dict[str, Any]:
    manifest = {
        "schema_version": schema_version,
        "run_id": run.id,
        "runtime_status": run.runtime_status,
        "outcome": run.outcome,
        "environment_snapshot_id": run.environment_snapshot_id,
        "timeline": [
            {
                "step_id": s.id,
                "sequence": s.sequence,
                "step_key": s.step_key,
                "step_type": s.step_type,
                "status": s.status,
                "trace_id": s.trace_id,
            }
            for s in steps
        ],
        "assertions": [
            {
                "assertion_id": a.id,
                "oracle_id": a.oracle_id,
                "result": a.result,
                "reason_code": a.reason_code,
            }
            for a in assertions
        ],
        "evidence": [
            {
                "artifact_id": e.id,
                "evidence_type": e.evidence_type,
                "storage_uri": e.storage_uri,
                "content_hash": e.content_hash,
                "sanitization_status": e.sanitization_status,
            }
            for e in evidence
        ],
    }
    return manifest


def manifest_hash(manifest: dict[str, Any]) -> str:
    text = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
