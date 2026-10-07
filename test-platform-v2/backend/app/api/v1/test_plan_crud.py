"""测试计划 API 路由（只读保留面） — /api/v1/test-plans/*

平台简化批次：旧测试计划体系前端入口已删（batch-212）、数据只读归档。
本文件只保留只读端点（列表/详情/统计），写入口（创建/编辑/删除/用例关联/指派）
已随「只读保留」决策删除；执行写入面见 test_plan_execution.py（同样收敛为只读）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.test_plan import PlanCaseOut, PlanDetailOut, PlanOut, PlanStats
from app.services import test_plan_service

router = APIRouter(prefix="/test-plans", tags=["测试计划"])


@router.get("", response_model=R[Page[PlanOut]])
def list_plans(
    status: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    current: CurrentUser = Depends(require_permission("testplan:list")),
    db: Session = Depends(get_db),
):
    items, total = test_plan_service.list_plans(
        db,
        project_id=current.project_id or 0,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return R.ok(Page(total=total, page=page, page_size=page_size, items=[PlanOut(**it) for it in items]))


@router.get("/{plan_id}", response_model=R[PlanDetailOut])
def get_plan(
    plan_id: int,
    current: CurrentUser = Depends(require_permission("testplan:detail")),
    db: Session = Depends(get_db),
):
    row = test_plan_service.get_plan(db, plan_id, project_id=current.project_id or 0)
    if not row:
        return R(code=404, msg="计划不存在")
    detail = PlanDetailOut(
        **{k: v for k, v in row.items() if k not in ("cases", "stats")},
        cases=[PlanCaseOut(**c) for c in row.get("cases", [])],
        stats=PlanStats(**row.get("stats", {})),
    )
    return R.ok(detail)


@router.get("/{plan_id}/stats", response_model=R[PlanStats])
def get_plan_stats(
    plan_id: int,
    current: CurrentUser = Depends(require_permission("testplan:detail")),
    db: Session = Depends(get_db),
):
    row = test_plan_service.get_plan(db, plan_id, project_id=current.project_id or 0)
    if not row:
        return R(code=404, msg="计划不存在")
    return R.ok(PlanStats(**row.get("stats", {})))
