"""Dashboard API — workbench statistics."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user, get_db
from app.schemas.common import R
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["工作台"])


@router.get("/stats", response_model=R[DashboardStats])
def get_dashboard_stats(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None, description="起始日期，格式 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="截止日期，格式 YYYY-MM-DD"),
):
    """获取当前项目的工作台统计（无需额外权限）。

    - 不传日期参数：默认统计近 7 天执行数据
    - 传 start_date / end_date：按自定义时间范围统计
    """
    from datetime import timedelta

    # 解析或使用默认值（近 7 天）
    parsed_start: date | None = None
    parsed_end: date | None = None

    if start_date:
        parsed_start = date.fromisoformat(start_date)
    if end_date:
        parsed_end = date.fromisoformat(end_date)

    # 如果都没传，默认近 7 天
    if not parsed_start and not parsed_end:
        today = date.today()
        parsed_start = today - timedelta(days=7)
        parsed_end = today

    stats = dashboard_service.get_dashboard_stats(
        db,
        project_id=current.project_id or 0,
        start_date=parsed_start,
        end_date=parsed_end,
    )
    return R.ok(DashboardStats(**stats))
