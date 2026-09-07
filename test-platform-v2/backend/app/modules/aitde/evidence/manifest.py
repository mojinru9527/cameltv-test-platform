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


def _json_value(raw: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except ValueError:
        return raw


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
                "id": s.id,
                "step_id": s.id,
                "run_id": s.run_id,
                "sequence": s.sequence,
                "step_key": s.step_key,
                "step_type": s.step_type,
                "status": s.status,
                "error_type": s.error_type,
                "error_message": s.error_message,
                "input_snapshot_json": _json_value(s.input_snapshot_json),
                "output_snapshot_json": _json_value(s.output_snapshot_json),
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
            }
            for s in steps
        ],
        "assertions": [
            {
                "id": a.id,
                "assertion_id": a.id,
                "run_id": a.run_id,
                "step_id": a.step_id,
                "oracle_id": a.oracle_id,
                "test_oracle_id": a.test_oracle_id,
                "oracle_source_type": a.oracle_source_type,
                "trust_status": a.trust_status,
                "binding_id": a.binding_id,
                "oracle_snapshot_json": _json_value(a.oracle_snapshot_json),
                "expected_json": _json_value(a.expected_json),
                "actual_json": _json_value(a.actual_json),
                "result": a.result,
                "reason_code": a.reason_code,
                "evidence_refs_json": _json_value(a.evidence_refs_json),
                "evaluated_at": a.evaluated_at.isoformat() if a.evaluated_at else None,
            }
            for a in assertions
        ],
        "evidence": [
            {
                "id": e.id,
                "artifact_id": e.id,
                "project_id": e.project_id,
                "run_id": e.run_id,
                "step_id": e.step_id,
                "evidence_type": e.evidence_type,
                "storage_provider": e.storage_provider,
                "storage_uri": e.storage_uri,
                "content_hash": e.content_hash,
                "content_type": e.content_type,
                "size_bytes": e.size_bytes,
                "sanitization_status": e.sanitization_status,
                "sensitivity": e.sensitivity,
                "retention_class": e.retention_class,
                "integrity_status": e.integrity_status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evidence
        ],
    }
    return manifest


def manifest_hash(manifest: dict[str, Any]) -> str:
    text = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
