"""C114-1 — 交互拓扑边 vs 用例覆盖缺口提示 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.schemas.interaction_coverage import InteractionGapRequest

router = APIRouter(prefix="/interaction-coverage", tags=["交互覆盖"])


@router.post("/gaps", response_model=R[dict], summary="交互拓扑覆盖缺口提示（C114-1）")
def interaction_coverage_gaps(
    body: InteractionGapRequest,
    current: CurrentUser = Depends(require_permission("knowledge:view")),
    db: Session = Depends(get_db),
):
    """对比交互拓扑边与平台交互用例，输出未覆盖边清单与覆盖率。"""
    from app.services.interaction_coverage_service import (
        compute_interaction_gaps,
        load_interaction_cases,
    )

    cases = load_interaction_cases(db, current.project_id or 0)
    result = compute_interaction_gaps(
        [e.model_dump() for e in body.edges],
        cases,
    )
    return R.ok(result)
