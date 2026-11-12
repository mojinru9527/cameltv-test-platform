"""batch-337（P1）：AIQE Workflow 定义列表 / 详情 / 审批 API。

- 统一要求执行中心权限 `menu:aiqe_runs`；审批写操作叠加 `defect:update`；
- 项目隔离：跨项目按不存在（404）处理，不泄露存在性；
- approved 后 graph/checksum 冻结（服务层 `update_graph` 已 fail-closed，本 API 只读 + 审批）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.aiqe.services.workflow_service import (
    WorkflowNotFound,
    approve_workflow,
    get_workflow_for_project,
    list_workflows,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/workflows", tags=["AIQE Workflow"])

_console_access = require_permission("menu:aiqe_runs")


def _not_found(workflow_id: str) -> APIException:
    return APIException(code=404, msg=f"Workflow 不存在: {workflow_id}", http_status=404)


def _workflow_out(row) -> dict:
    graph = row.graph_json or {}
    return {
        "id": row.id,
        "scenario_id": row.scenario_id,
        "version": row.version,
        "schema_version": row.schema_version,
        "checksum": row.checksum,
        "validation_status": row.validation_status,
        "approval_status": row.approval_status,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at,
        "created_at": row.created_at,
        "node_count": len(graph.get("nodes") or []),
        "frozen": row.approval_status == "approved",
    }


@router.get("", response_model=R[dict], summary="Workflow 定义列表")
def list_workflows_api(
    approval_status: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows, total = list_workflows(
        db,
        current.project_id or 0,
        limit=limit,
        offset=offset,
        approval_status=approval_status,
    )
    return R.ok({"items": [_workflow_out(row) for row in rows], "total": total})


@router.get("/{workflow_id}", response_model=R[dict], summary="Workflow 定义详情")
def get_workflow_api(
    workflow_id: str,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    try:
        row = get_workflow_for_project(db, workflow_id, current.project_id or 0)
    except WorkflowNotFound:
        raise _not_found(workflow_id) from None
    data = _workflow_out(row)
    data["graph_json"] = row.graph_json
    return R.ok(data)


@router.post("/{workflow_id}/approve", response_model=R[dict], summary="审批 Workflow（approved 冻结）")
def approve_workflow_api(
    workflow_id: str,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = get_workflow_for_project(db, workflow_id, current.project_id or 0)
    except WorkflowNotFound:
        raise _not_found(workflow_id) from None
    row = approve_workflow(db, row.id, approved_by=current.user.id)
    return R.ok(_workflow_out(row))
