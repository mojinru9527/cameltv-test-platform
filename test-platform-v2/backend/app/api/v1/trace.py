"""Trace & coverage API — requirement → case → plan → execution → defect matrix."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, get_current_user, require_project
from app.core.db import get_db
from app.schemas.common import R
from app.services import trace_service

router = APIRouter(prefix="/trace", tags=["追溯矩阵"])


@router.get("/coverage", response_model=R[dict], summary="项目级覆盖率矩阵")
def coverage(
    current: CurrentUser = Depends(require_project),
    db=Depends(get_db),
):
    """返回项目维度覆盖率：用例→计划→执行→缺陷 的统计矩阵。"""
    result = trace_service.get_project_coverage(db, current.project_id)
    return R(data=result)


@router.get("/trend", response_model=R[dict], summary="通过率趋势")
def trend(
    days: int = 30,
    current: CurrentUser = Depends(require_project),
    db=Depends(get_db),
):
    """返回最近 N 天的每日执行通过率趋势。"""
    result = trace_service.get_trend(db, current.project_id, days=min(days, 180))
    return R(data=result)


@router.get("/case/{case_id}", response_model=R[dict], summary="用例追溯详情")
def case_trace(
    case_id: int,
    current: CurrentUser = Depends(require_project),
    db=Depends(get_db),
):
    """返回单个用例的完整追溯链：关联的计划→执行记录→缺陷。"""
    result = trace_service.get_case_trace(db, case_id, current.project_id)
    if result is None:
        from app.core.exceptions import not_found
        raise not_found("用例不存在")
    return R(data=result)


@router.get("/requirement/{doc_id}", response_model=R[dict], summary="需求覆盖率详情")
def requirement_coverage(
    doc_id: int,
    current: CurrentUser = Depends(require_project),
    db=Depends(get_db),
):
    """返回单个需求文档的覆盖率：关联用例→计划→执行→缺陷的完整矩阵。"""
    result = trace_service.get_requirement_coverage(db, doc_id, current.project_id)
    if result is None:
        from app.core.exceptions import not_found
        raise not_found("需求文档不存在")
    return R(data=result)
