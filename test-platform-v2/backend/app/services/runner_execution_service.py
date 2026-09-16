"""Historical internal-runner task reads.

Canonical API/UI/external execution uses
``app.modules.campaign_execution.service.claim_execution_run`` and the
``/api/v1/execution/runs/*`` endpoints.  The old queue writers are removed;
this module intentionally exposes only the historical read surface.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.runner_execution import RunnerExecutionTask


def list_runner_tasks(db: Session, project_id: int, status: str | None = None) -> list[RunnerExecutionTask]:
    q = db.query(RunnerExecutionTask).filter(RunnerExecutionTask.project_id == project_id)
    if status:
        q = q.filter(RunnerExecutionTask.status == status)
    return q.order_by(RunnerExecutionTask.id.desc()).limit(100).all()
