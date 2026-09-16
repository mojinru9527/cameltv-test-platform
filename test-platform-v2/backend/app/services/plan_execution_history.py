"""Read-only history for the retired PlanExecutionJob dispatch queue."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan_execution_job import PlanExecutionJob


def list_jobs(db: Session, plan_id: int, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(PlanExecutionJob)
        .where(
            PlanExecutionJob.plan_id == plan_id,
            PlanExecutionJob.project_id == project_id,
        )
        .order_by(PlanExecutionJob.id.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": row.id,
            "plan_id": row.plan_id,
            "status": row.status,
            "result": json.loads(row.result_json or "{}"),
            "error_message": row.error_message,
            "created_at": row.created_at,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
        }
        for row in rows
    ]
