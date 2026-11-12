"""batch-339（P1）：平台矩阵只读 API（真实节点能力数据）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.aiqe.services.platform_matrix import build_platform_matrix
from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/platform-matrix", tags=["AIQE Platform Matrix"])

_console_access = require_permission("menu:aiqe_runs")


@router.get("", response_model=R[dict], summary="平台 × 能力矩阵（节点自描述真实数据）")
def get_platform_matrix_api(
    _console: CurrentUser = Depends(_console_access),
    db: Session = Depends(get_db),
):
    return R.ok(build_platform_matrix(db))
