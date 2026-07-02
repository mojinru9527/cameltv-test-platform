"""Environment & Variable management API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.schemas.common import R
from app.schemas.environment import (
    EnvironmentCreate, EnvironmentUpdate, EnvironmentResponse,
    VariableCreate, VariableUpdate, VariableResponse,
    VariableResolveRequest, VariableResolveResponse,
)
from app.services import environment_service as svc

router = APIRouter(prefix="/environments", tags=["环境变量管理"])


# ── Environment CRUD ──

@router.get("", response_model=R[list[EnvironmentResponse]], summary="环境列表")
def list_environments(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = svc.list_environments(db, current.project_id or 0)
    return R.ok(rows)


@router.post("", response_model=R[EnvironmentResponse], summary="创建环境")
def create_environment(
    body: EnvironmentCreate,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    row = svc.create_environment(db, current.project_id or 0, body.model_dump())
    return R.ok(row)


@router.put("/{env_id}", response_model=R[EnvironmentResponse], summary="更新环境")
def update_environment(
    env_id: int,
    body: EnvironmentUpdate,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    svc.get_environment(db, env_id, current.project_id or 0)  # 404 if not found
    row = svc.update_environment(db, env_id, body.model_dump(exclude_none=True))
    return R.ok(row)


@router.delete("/{env_id}", response_model=R[dict], summary="删除环境")
def delete_environment(
    env_id: int,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    svc.get_environment(db, env_id, current.project_id or 0)  # 404 if not found
    svc.delete_environment(db, env_id)
    return R.ok({"deleted": True})


# ── Variable CRUD ──

@router.get("/{env_id}/variables", response_model=R[list[VariableResponse]], summary="变量列表")
def list_variables(
    env_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc.get_environment(db, env_id, current.project_id or 0)  # 404 if not found
    rows = svc.list_variables(db, env_id)
    return R.ok(rows)


@router.post("/{env_id}/variables", response_model=R[VariableResponse], summary="创建变量")
def create_variable(
    env_id: int,
    body: VariableCreate,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    svc.get_environment(db, env_id, current.project_id or 0)  # 404 if not found
    row = svc.create_variable(db, env_id, body.model_dump())
    return R.ok(row)


@router.put("/{env_id}/variables/{var_id}", response_model=R[VariableResponse], summary="更新变量")
def update_variable(
    env_id: int,
    var_id: int,
    body: VariableUpdate,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    svc.get_environment(db, env_id, current.project_id or 0)  # 404 if not found
    row = svc.update_variable(db, var_id, body.model_dump(exclude_none=True))
    if not row:
        return R.err(code=404, msg="变量不存在")
    return R.ok(row)


@router.delete("/{env_id}/variables/{var_id}", response_model=R[dict], summary="删除变量")
def delete_variable(
    env_id: int,
    var_id: int,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    svc.get_environment(db, env_id, current.project_id or 0)  # 404 if not found
    ok = svc.delete_variable(db, var_id)
    if not ok:
        return R.err(code=404, msg="变量不存在")
    return R.ok({"deleted": True})


# ── Resolve ──

@router.post("/resolve", response_model=R[VariableResolveResponse], summary="解析变量引用")
def resolve_variables(
    body: VariableResolveRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc.get_environment(db, body.environment_id, current.project_id or 0)  # 404 if not found
    resolved = svc.resolve_variables(db, body.environment_id, body.template)
    return R.ok({"resolved": resolved})
