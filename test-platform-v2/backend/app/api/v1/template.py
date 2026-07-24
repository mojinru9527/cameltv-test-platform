"""Report template CRUD API routes."""
from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import template_service

router = APIRouter(prefix="/report-templates", tags=["报告模板"])


# ── Request/Response schemas ──

class TemplateSection(BaseModel):
    key: str = ""
    label: str = ""
    enabled: bool = True
    order: int = 0


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    sections: list[TemplateSection] = []
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sections: list[TemplateSection] | None = None
    is_default: bool | None = None


# ── CRUD ──

@router.get("", response_model=R[dict], summary="报告模板列表")
def list_templates(
    current: CurrentUser = Depends(require_permission("report:list")),
    db: Session = Depends(get_db),
):
    """获取当前项目下所有报告模板。"""
    items = template_service.list_templates(db, current.project_id or 0)
    return R.ok({"total": len(items), "items": items})


@router.post("", response_model=R[dict], summary="创建报告模板")
def create_template(
    body: TemplateCreate,
    current: CurrentUser = Depends(require_permission("report:create")),
    db: Session = Depends(get_db),
):
    """创建新的报告模板。设为默认时自动取消其他模板的默认标记。"""
    result = template_service.create_template(db, current.project_id or 0, body)
    db.commit()
    return R.ok(result)


@router.put("/{template_id}", response_model=R[dict], summary="更新报告模板")
def update_template(
    template_id: int,
    body: TemplateUpdate,
    current: CurrentUser = Depends(require_permission("report:create")),
    db: Session = Depends(get_db),
):
    """更新报告模板。"""
    result = template_service.update_template(db, template_id, current.project_id or 0, body)
    if not result:
        from app.core.exceptions import not_found
        raise not_found("模板")
    db.commit()
    return R.ok(result)


@router.delete("/{template_id}", response_model=R[dict], summary="删除报告模板")
def delete_template(
    template_id: int,
    current: CurrentUser = Depends(require_permission("report:delete")),
    db: Session = Depends(get_db),
):
    """删除报告模板。"""
    ok = template_service.delete_template(db, template_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("模板")
    db.commit()
    return R.ok({"deleted": True})


@router.get("/{template_id}", response_model=R[dict], summary="报告模板详情")
def get_template(
    template_id: int,
    current: CurrentUser = Depends(require_permission("report:list")),
    db: Session = Depends(get_db),
):
    """获取单个报告模板详情（含展开的 sections）。"""
    result = template_service.preview_template(db, template_id, current.project_id or 0)
    if not result:
        from app.core.exceptions import not_found
        raise not_found("模板")
    return R.ok(result)
