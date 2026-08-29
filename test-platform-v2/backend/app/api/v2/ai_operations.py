"""AITDE v2 AI Operation API (V30-084)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.ai_ops import service
from app.modules.aitde.ai_ops.models import AIOperationRecord
from app.schemas.common import R

router = APIRouter(
    prefix="/ai-operations",
    tags=["AITDE - AI Governance"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.get("/{operation_id}", response_model=R[dict])
def get_operation(
    operation_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    record = service.get_operation(db, operation_id)
    return R.ok(_to_dict(record))


def _to_dict(row: AIOperationRecord) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "operation_type": row.operation_type,
        "status": row.status,
        "model_provider": row.model_provider,
        "model_name": row.model_name,
        "prompt_version": row.prompt_version,
        "schema_version": row.schema_version,
        "result_ref_json": row.result_ref_json,
        "error_code": row.error_code,
        "error_message": row.error_message,
        "duration_ms": row.duration_ms,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }
