"""AITDE V3.1 execution model → dict mappers (V31)."""
from __future__ import annotations

from typing import Any

from app.modules.aitde.execution.models import (
    AssertionResult,
    EnvironmentSnapshot,
    EvidenceArtifact,
    ExecutionRun,
    ExecutionStep,
    ReplayManifest,
    ScenarioAdapter,
)


def adapter_to_dict(row: ScenarioAdapter) -> dict[str, Any]:
    return {
        "id": row.id,
        "scenario_id": row.scenario_id,
        "scenario_version_id": row.scenario_version_id,
        "adapter_type": row.adapter_type,
        "status": row.status,
        "source_asset_type": row.source_asset_type,
        "source_asset_id": row.source_asset_id,
        "config_json": row.config_json,
        "adapter_version": row.adapter_version,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def snapshot_to_dict(row: EnvironmentSnapshot) -> dict[str, Any]:
    return {
        "id": row.id,
        "environment_id": row.environment_id,
        "mission_id": row.mission_id,
        "build_label": row.build_label,
        "frontend_version": row.frontend_version,
        "service_versions_json": row.service_versions_json,
        "openapi_hash": row.openapi_hash,
        "db_schema_version": row.db_schema_version,
        "config_hash": row.config_hash,
        "static_asset_hash": row.static_asset_hash,
        "manual_note": row.manual_note,
        "fingerprint_hash": row.fingerprint_hash,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
        "created_by_type": row.created_by_type,
    }


def run_to_dict(row: ExecutionRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "scenario_id": row.scenario_id,
        "scenario_version_id": row.scenario_version_id,
        "contract_version_id": row.contract_version_id,
        "adapter_id": row.adapter_id,
        "environment_id": row.environment_id,
        "environment_snapshot_id": row.environment_snapshot_id,
        "runtime_status": row.runtime_status,
        "outcome": row.outcome,
        "evidence_status": row.evidence_status,
        "trigger_type": row.trigger_type,
        "parent_run_id": row.parent_run_id,
        "retry_no": row.retry_no,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "duration_ms": row.duration_ms,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def step_to_dict(row: ExecutionStep) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "sequence": row.sequence,
        "step_key": row.step_key,
        "step_type": row.step_type,
        "status": row.status,
        "error_type": row.error_type,
        "error_message": row.error_message,
        "input_snapshot_json": row.input_snapshot_json,
        "output_snapshot_json": row.output_snapshot_json,
        "trace_id": row.trace_id,
        "span_id": row.span_id,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }


def assertion_to_dict(row: AssertionResult) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "step_id": row.step_id,
        "oracle_id": row.oracle_id,
        "oracle_snapshot_json": row.oracle_snapshot_json,
        "expected_json": row.expected_json,
        "actual_json": row.actual_json,
        "result": row.result,
        "reason_code": row.reason_code,
        "evidence_refs_json": row.evidence_refs_json,
        "evaluated_at": row.evaluated_at.isoformat() if row.evaluated_at else None,
    }


def evidence_to_dict(row: EvidenceArtifact) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "run_id": row.run_id,
        "step_id": row.step_id,
        "evidence_type": row.evidence_type,
        "storage_provider": row.storage_provider,
        "storage_uri": row.storage_uri,
        "content_hash": row.content_hash,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "sanitization_status": row.sanitization_status,
        "sensitivity": row.sensitivity,
        "retention_class": row.retention_class,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def replay_to_dict(row: ReplayManifest) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "schema_version": row.schema_version,
        "manifest_json": row.manifest_json,
        "manifest_hash": row.manifest_hash,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }
