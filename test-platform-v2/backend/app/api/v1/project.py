"""项目路由 —— 用户项目列表 / 项目管理 CRUD / 成员管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission, require_project
from app.schemas.common import R
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import project_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/projects", tags=["项目"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    write_audit(
        db, user_id=cu.user.id, username=cu.user.username or "",
        project_id=cu.project_id or 0, action=action, target=target, detail=detail,
        ip=req.client.host if req.client else "",
    )


# ── User endpoints ──

@router.get("", response_model=R[list[ProjectOut]], summary="当前用户可见项目")
def list_projects(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = project_service.projects_for_user(db, current.user.id, is_superadmin=current.is_super)
    return R.ok([ProjectOut.model_validate(p) for p in projects])


@router.get("/current", response_model=R[ProjectOut], summary="校验并返回当前项目（需 X-Project-Id）")
def current_project(current: CurrentUser = Depends(require_project), db: Session = Depends(get_db)):
    from app.models.project import Project
    from app.core.exceptions import not_found
    proj = db.get(Project, current.project_id)
    if not proj:
        raise not_found("项目")
    return R.ok(ProjectOut.model_validate(proj))


# ── Admin endpoints ──

@router.get("/all", response_model=R[dict], summary="全量项目列表（管理）")
def list_all_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("project:list")),
    db: Session = Depends(get_db),
):
    items, total = project_service.list_all_projects(db, page=page, page_size=page_size)
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


@router.get("/{project_id}", response_model=R[dict], summary="项目详情")
def get_project(
    project_id: int,
    current: CurrentUser = Depends(require_permission("project:detail")),
    db: Session = Depends(get_db),
):
    r = project_service.get_project(db, project_id)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("项目")
    return R.ok(r)


@router.post("", response_model=R[ProjectOut], summary="创建项目")
def create_project(
    req: Request, body: ProjectCreate,
    current: CurrentUser = Depends(require_permission("project:create")),
    db: Session = Depends(get_db),
):
    r = project_service.create_project(db, body, current.user.id)
    db.commit()
    _audit(req, current, db, "project:create", f"#{r['id']} {r['name']}")
    return R.ok(ProjectOut(**r))


@router.put("/{project_id}", response_model=R[dict], summary="编辑项目")
def update_project(
    req: Request, project_id: int, body: ProjectUpdate,
    current: CurrentUser = Depends(require_permission("project:update")),
    db: Session = Depends(get_db),
):
    r = project_service.update_project(db, project_id, body)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("项目")
    db.commit()
    _audit(req, current, db, "project:update", f"#{project_id}")
    return R.ok(r)


@router.delete("/{project_id}", response_model=R[dict], summary="删除项目")
def delete_project(
    req: Request, project_id: int,
    current: CurrentUser = Depends(require_permission("project:delete")),
    db: Session = Depends(get_db),
):
    ok = project_service.delete_project(db, project_id)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("项目")
    db.commit()
    _audit(req, current, db, "project:delete", f"project #{project_id}")
    return R.ok({"deleted": True})


@router.post("/{project_id}/members", response_model=R[dict], summary="添加/更新项目成员")
def add_member(
    req: Request, project_id: int,
    body: dict,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    user_id = body.get("user_id", 0)
    role_id = body.get("role_id", 0)
    r = project_service.add_member(db, project_id, user_id, role_id)
    db.commit()
    _audit(req, current, db, "project:member:add", f"project#{project_id} user#{user_id}")
    return R.ok(r)


@router.delete("/{project_id}/members/{user_id}", response_model=R[dict], summary="移除项目成员")
def remove_member(
    req: Request, project_id: int, user_id: int,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    ok = project_service.remove_member(db, project_id, user_id)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("项目成员")
    db.commit()
    _audit(req, current, db, "project:member:remove", f"project#{project_id} user#{user_id}")
    return R.ok({"deleted": True})


@router.get("/{project_id}/members", response_model=R[list], summary="项目成员列表")
def list_members(
    project_id: int,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    items = project_service.list_members(db, project_id)
    return R.ok(items)


# ── Quality Gate Config ────────────────────────────────

from pydantic import BaseModel as _PydanticBase


class GateConfigBody(_PydanticBase):
    pass_rate_threshold: int | None = 80   # 0-100
    p0_max: int | None = 0
    p1_max: int | None = 5
    enabled: bool | None = True


@router.get("/{project_id}/quality-gate", response_model=R[dict], summary="获取质量门禁配置")
def get_quality_gate(
    project_id: int,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    """获取项目的质量门禁配置。未配置时返回默认值。"""
    from app.services.report_service import get_quality_gate_config

    config = get_quality_gate_config(db, project_id)
    if not config:
        return R.ok({
            "project_id": project_id,
            "pass_rate_threshold": 80,
            "p0_max": 0,
            "p1_max": 5,
            "enabled": True,
            "is_default": True,
        })
    return R.ok({**config, "is_default": False})


@router.put("/{project_id}/quality-gate", response_model=R[dict], summary="配置质量门禁")
def upsert_quality_gate(
    project_id: int,
    body: GateConfigBody,
    req: Request,
    current: CurrentUser = Depends(require_permission("project:manage")),
    db: Session = Depends(get_db),
):
    """创建或更新项目的质量门禁配置。"""
    from app.services.report_service import save_quality_gate_config

    config = save_quality_gate_config(
        db, project_id, body.model_dump(exclude_none=True)
    )
    db.commit()
    _audit(req, current, db, "project:gate:config", f"project#{project_id} gate updated")
    return R.ok({**config, "is_default": False})
