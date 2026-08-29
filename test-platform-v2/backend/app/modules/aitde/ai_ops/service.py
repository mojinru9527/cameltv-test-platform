"""AI operation service (V30-080..V30-084).

Records structured AI operation results for audit/observability and provides the
SourceRef validator + a bounded (1 retry) structured-repair helper. The record
never stores chain-of-thought, only structured input/output summaries.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.ai_ops.models import AIOperationRecord
from app.modules.aitde.common.enums import AIOperationStatus


def create_operation(
    db: Session,
    project_id: int,
    mission_id: int,
    operation_type: str,
    user_id: int = 0,
) -> AIOperationRecord:
    row = AIOperationRecord(
        project_id=project_id,
        mission_id=mission_id,
        operation_type=operation_type,
        status=AIOperationStatus.QUEUED.value,
        created_by=user_id,
        started_at=datetime.now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_operation(db: Session, operation_id: int) -> AIOperationRecord:
    row = db.get(AIOperationRecord, operation_id)
    if not row:
        raise APIException(code=404, msg="AI 操作记录不存在", http_status=404)
    return row


def list_operations(
    db: Session,
    mission_id: int,
    project_id: int,
    *,
    limit: int = 50,
) -> list[AIOperationRecord]:
    """List a mission's AI operation records, newest first (v331-remediation-2
    B2 / V30-085). Project-scoped via project_id; bounded page for the drawer."""
    return list(
        db.scalars(
            select(AIOperationRecord)
            .where(
                AIOperationRecord.mission_id == mission_id,
                AIOperationRecord.project_id == project_id,
            )
            .order_by(AIOperationRecord.id.desc())
            .limit(limit)
        ).all()
    )


def mark_running(db: Session, operation: AIOperationRecord) -> AIOperationRecord:
    operation.status = AIOperationStatus.RUNNING.value
    operation.started_at = operation.started_at or datetime.now()
    db.commit()
    db.refresh(operation)
    return operation


def mark_succeeded(
    db: Session,
    operation: AIOperationRecord,
    *,
    result_ref: dict[str, Any] | None = None,
    output_hash: str = "",
    token_usage: dict[str, Any] | None = None,
    duration_ms: int = 0,
) -> AIOperationRecord:
    operation.status = AIOperationStatus.SUCCEEDED.value
    operation.result_ref_json = json.dumps(result_ref or {}, ensure_ascii=False)
    operation.output_hash = output_hash
    operation.token_usage_json = json.dumps(token_usage or {}, ensure_ascii=False)
    operation.duration_ms = duration_ms
    operation.finished_at = datetime.now()
    db.commit()
    db.refresh(operation)
    return operation


def mark_failed(
    db: Session,
    operation: AIOperationRecord,
    *,
    code: str = "",
    message: str = "",
) -> AIOperationRecord:
    operation.status = AIOperationStatus.FAILED.value
    operation.error_code = code
    operation.error_message = message
    operation.finished_at = datetime.now()
    db.commit()
    db.refresh(operation)
    return operation


def validate_source_refs(db: Session, source_refs: list[dict]) -> list[str]:
    """Ensure AI source refs point to existing sources (V30-082).

    Returns a list of invalid ref descriptions; empty = all valid. Refs with
    artifact_id <= 0 are treated as placeholders and skipped.
    """
    from app.modules.aitde.sources.models import SourceArtifact

    invalid: list[str] = []
    for ref in source_refs:
        artifact_id = int(ref.get("artifact_id") or 0)
        if artifact_id <= 0:
            continue
        exists = db.scalar(
            select(SourceArtifact).where(SourceArtifact.id == artifact_id)
        )
        if not exists:
            invalid.append(f"artifact_id={artifact_id}")
    return invalid


def repair_retry(call: Callable[[], Any], *, max_retries: int = 1) -> Any:
    """Structured repair retry (V30-083): allow at most `max_retries` retries."""
    attempt = 0
    while True:
        try:
            return call()
        except Exception:  # noqa: BLE001  (repair boundary: records and retries once)
            attempt += 1
            if attempt > max_retries:
                raise
