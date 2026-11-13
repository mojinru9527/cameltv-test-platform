"""batch-337（P1）：AIQE Workflow 定义列表 / 详情 / 审批 API。

- 统一要求执行中心权限 `menu:aiqe_runs`；审批写操作叠加 `defect:update`；
- 项目隔离：跨项目按不存在（404）处理，不泄露存在性；
- approved 后 graph/checksum 冻结（服务层 `update_graph` 已 fail-closed，本 API 只读 + 审批）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.aiqe.services.capability_registry import known_capabilities
from app.aiqe.services.workflow_service import (
    WorkflowImmutableError,
    WorkflowNotFound,
    approve_workflow,
    create_workflow,
    get_workflow_for_project,
    list_workflows,
    update_graph,
)
from app.aiqe.services.workflow_validator import (
    WorkflowValidationError,
    validate_workflow,
)
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/workflows", tags=["AIQE Workflow"])

_console_access = require_permission("menu:aiqe_runs")

DEFAULT_DRIVERS = frozenset(
    {"http", "playwright", "db", "event", "mobile", "miniapp", "device", "external_e2e"}
)


class WorkflowCreateIn(BaseModel):
    graph: dict
    scenario_id: int | None = None
    version: int | None = None


class WorkflowPatchIn(BaseModel):
    graph: dict


def _validate(graph: dict) -> None:
    try:
        validate_workflow(
            graph,
            registered_drivers=set(DEFAULT_DRIVERS),
            registered_capabilities=set(known_capabilities()),
        )
    except WorkflowValidationError as exc:
        raise APIException(code=400, msg=f"Workflow 校验失败: {exc}", http_status=400) from None


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


@router.post("", response_model=R[dict], summary="创建 Workflow 定义（校验 + checksum）")
def create_workflow_api(
    body: WorkflowCreateIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    _validate(body.graph)
    row = create_workflow(
        db,
        project_id=current.project_id or 0,
        graph=body.graph,
        scenario_id=body.scenario_id,
        version=body.version,
    )
    return R.ok(_workflow_out(row))


@router.patch("/{workflow_id}", response_model=R[dict], summary="更新 Workflow graph（approved 后 409）")
def patch_workflow_api(
    workflow_id: str,
    body: WorkflowPatchIn,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        get_workflow_for_project(db, workflow_id, current.project_id or 0)
    except WorkflowNotFound:
        raise _not_found(workflow_id) from None
    _validate(body.graph)
    try:
        row = update_graph(db, workflow_id, body.graph)
    except WorkflowImmutableError as exc:
        raise APIException(code=409, msg=str(exc), http_status=409) from None
    except WorkflowNotFound:
        raise _not_found(workflow_id) from None
    return R.ok(_workflow_out(row))


@router.post("/{workflow_id}/approve", response_model=R[dict], summary="审批 Workflow（approved 冻结）")
def approve_workflow_api(
    workflow_id: str,
    _console: CurrentUser = Depends(_console_access),
    current: CurrentUser = Depends(require_permission("aiqe:workflow:approve")),
    db: Session = Depends(get_db),
):
    try:
        row = get_workflow_for_project(db, workflow_id, current.project_id or 0)
    except WorkflowNotFound:
        raise _not_found(workflow_id) from None
    row = approve_workflow(db, row.id, approved_by=current.user.id)
    return R.ok(_workflow_out(row))
