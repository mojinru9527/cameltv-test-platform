"""ShadowAudit (V31-015).

Tester deep-audit feedback on a Run's outcome: CONFIRMED / FALSE_PASS /
FALSE_FAIL. Feedback is append-only and NEVER mutates the Run's historical
``outcome`` — the audit is a monitoring/learning signal, not a verdict override.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.execution import service
from app.modules.aitde.execution.models import ShadowAuditFeedback

VALID_AUDIT_OUTCOMES = {"CONFIRMED", "FALSE_PASS", "FALSE_FAIL"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def submit_feedback(
    db: Session,
    run_id: int,
    project_id: int,
    audit_outcome: str,
    reason: str,
    user_id: int,
) -> ShadowAuditFeedback:
    service.get_run(db, run_id, project_id)  # raises 404 if not in project
    if audit_outcome not in VALID_AUDIT_OUTCOMES:
        raise APIException(
            code=400, msg=f"非法审计结论：{audit_outcome}", http_status=400
        )
    row = ShadowAuditFeedback(
        run_id=run_id,
        audit_outcome=audit_outcome,
        reason=reason or "",
        created_by=user_id,
        created_at=_utcnow(),
    )
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return row


def list_feedback(db: Session, run_id: int, project_id: int) -> list[ShadowAuditFeedback]:
    service.get_run(db, run_id, project_id)  # 404 if not in project
    return list(
        db.scalars(
            select(ShadowAuditFeedback)
            .where(ShadowAuditFeedback.run_id == run_id)
            .order_by(ShadowAuditFeedback.id.desc())
        ).all()
    )


def feedback_to_dict(row: ShadowAuditFeedback) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "audit_outcome": row.audit_outcome,
        "reason": row.reason,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
