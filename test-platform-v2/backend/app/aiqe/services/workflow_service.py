"""M2 / TA-010：Workflow 定义存储 + 审批冻结（13 号 §4.6）。"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.aiqe.models.workflow import WorkflowDefinition
from app.aiqe.services.workflow_validator import workflow_checksum


class WorkflowImmutableError(ValueError):
    """approved 后禁止修改 graph/checksum。"""


class WorkflowNotFound(LookupError):
    pass


def create_workflow(
    db: Session,
    *,
    project_id: int,
    graph: dict[str, Any],
    scenario_id: int | None = None,
    version: int | None = None,
    validation_status: str = "draft",
) -> WorkflowDefinition:
    if version is None:
        current = db.scalar(
            select(func.max(WorkflowDefinition.version)).where(
                WorkflowDefinition.scenario_id == scenario_id
            )
        )
        version = int(current or 0) + 1
    row = WorkflowDefinition(
        project_id=project_id,
        scenario_id=scenario_id,
        version=version,
        graph_json=graph,
        schema_version=str(graph.get("schema_version") or "1.0"),
        checksum=workflow_checksum(graph),
        validation_status=validation_status,
    )
    db.add(row)
    db.flush()
    return row


def approve_workflow(
    db: Session, workflow_id: str, approved_by: int | None = None
) -> WorkflowDefinition:
    row = db.get(WorkflowDefinition, workflow_id)
    if row is None:
        raise WorkflowNotFound(workflow_id)
    if row.approval_status == "approved":
        return row
    row.approval_status = "approved"
    row.approved_by = approved_by
    row.approved_at = datetime.now(UTC)
    row.validation_status = "valid"
    row.checksum = workflow_checksum(row.graph_json)
    db.flush()
    return row


def update_graph(
    db: Session, workflow_id: str, graph: dict[str, Any]
) -> WorkflowDefinition:
    row = db.get(WorkflowDefinition, workflow_id)
    if row is None:
        raise WorkflowNotFound(workflow_id)
    if row.approval_status == "approved":
        raise WorkflowImmutableError("approved workflow 不可修改，请新建 version")
    row.graph_json = graph
    row.schema_version = str(graph.get("schema_version") or "1.0")
    row.checksum = workflow_checksum(graph)
    db.flush()
    return row


def get_workflow(db: Session, workflow_id: str) -> WorkflowDefinition:
    row = db.get(WorkflowDefinition, workflow_id)
    if row is None:
        raise WorkflowNotFound(workflow_id)
    return row
