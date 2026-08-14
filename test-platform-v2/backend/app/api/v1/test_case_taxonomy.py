"""测试用例 API 路由（域树/分类） — /api/v1/test-cases/*

Batch 181（FIX-173-P2-10）路由拆分：原 test_case.py 中的域/模块/分类端点
（GET /domains、/stats、/taxonomy、POST/DELETE /domains...）拆分至此。
端点函数体逐字移动，仅调整 import。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.schemas.common import R
from app.schemas.test_case import (
    DomainCreate,
    DomainNode,
    ModuleCreate,
    TaxonomySurfaceNode,
)
from app.services import audit_service, test_case_service

router = APIRouter(prefix="/test-cases", tags=["测试用例-分类"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    audit_service.write_audit(
        db,
        user_id=cu.user.id,
        username=cu.user.username,
        project_id=cu.project_id or 0,
        action=action,
        target=target,
        detail=detail,
        ip=req.client.host if req.client else "",
    )


# ── 域树 ──────────────────────────────────────────────

@router.get("/domains", response_model=R[list[DomainNode]])
def list_domains(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tree = test_case_service.get_category_tree(db, project_id=current.project_id or 0)
    return R.ok(tree)


@router.get("/stats", response_model=R[dict], summary="用例类型统计")
def get_test_case_stats(
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """Return authoritative project totals before the dynamic ``/{case_id}`` route."""
    return R.ok(test_case_service.get_stats(db, project_id=current.project_id or 0))


@router.get("/taxonomy", response_model=R[list[TaxonomySurfaceNode]], summary="用例多级分类")
def get_test_case_taxonomy(
    case_type: str = "manual",
    surface: str = "",
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """默认返回功能用例，并按用户端/运营后台/接口测试组织多级模块。"""
    return R.ok(test_case_service.get_taxonomy(
        db,
        project_id=current.project_id or 0,
        case_type=case_type,
        surface=surface,
    ))


@router.post("/domains", response_model=R[dict], summary="新增域")
def add_domain(
    body: DomainCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    try:
        result = test_case_service.create_domain(db, project_id=current.project_id or 0, name=body.name)
        _audit(req, current, db, "create", f"domain/{body.name}", f"新增域: {body.name}")
        return R.ok(result)
    except ValueError as e:
        return R.err(code=400, msg=str(e))


@router.delete("/domains/{domain_id}", response_model=R[dict], summary="删除域")
def remove_domain(
    domain_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:delete")),
    db: Session = Depends(get_db),
):
    ok = test_case_service.delete_domain(db, domain_id=domain_id, project_id=current.project_id or 0)
    if not ok:
        return R.err(code=404, msg="域不存在")
    _audit(req, current, db, "delete", f"domain/{domain_id}")
    return R.ok({"deleted": True})


@router.post("/domains/{domain_id}/modules", response_model=R[dict], summary="新增模块")
def add_module(
    domain_id: int,
    body: ModuleCreate,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    try:
        result = test_case_service.create_module(
            db, domain_id=domain_id, project_id=current.project_id or 0, name=body.name
        )
        _audit(req, current, db, "create", f"module/{body.name}")
        return R.ok(result)
    except ValueError as e:
        return R.err(code=400, msg=str(e))


@router.delete("/domains/{domain_id}/modules/{module_id}", response_model=R[dict], summary="删除模块")
def remove_module(
    domain_id: int,
    module_id: int,
    req: Request,
    current: CurrentUser = Depends(require_permission("testcase:delete")),
    db: Session = Depends(get_db),
):
    ok = test_case_service.delete_module(db, domain_id=domain_id, module_id=module_id)
    if not ok:
        return R.err(code=404, msg="模块不存在")
    _audit(req, current, db, "delete", f"module/{module_id}")
    return R.ok({"deleted": True})
