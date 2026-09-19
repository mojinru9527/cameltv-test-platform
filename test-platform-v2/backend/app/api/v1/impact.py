"""影响面查询（Batch 260 / B3-3）。

只读为主：回答"改了 X 要跑哪些"。重建关联是显式动作且需要单独权限点
（不复用 uitest:*，与 Batch 243 的 `uitest:code_execute` 教训一致：不同能力的权限不要互相借）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services import impact_graph_service, impact_query_service

router = APIRouter(prefix="/impact", tags=["Impact"])


class RebuildRequest(BaseModel):
    bundle_id: int = Field(..., ge=1)
    dry_run: bool = False


def _project_id(current: CurrentUser) -> int:
    if not current.project_id:
        raise HTTPException(400, "缺少当前项目上下文")
    return current.project_id


@router.get("/what-to-run", response_model=R[dict], summary="改了 X 要跑哪些（知识主线）")
def what_to_run(
    module: str = Query(min_length=1, max_length=200, description="变更的模块名"),
    version: str = Query(default="", max_length=80, description="可选：限定版本"),
    current: CurrentUser = Depends(require_permission("impact:view")),
    db: Session = Depends(get_db),
):
    return R.ok(
        impact_query_service.what_to_run(
            db, project_id=_project_id(current), module=module, version=version
        )
    )


@router.post("/rebuild", response_model=R[dict], summary="重建影响图关联（需求变更→模块→用例）")
def rebuild(
    body: RebuildRequest,
    current: CurrentUser = Depends(require_permission("impact:manage")),
    db: Session = Depends(get_db),
):
    result = impact_graph_service.build_edges(
        db, project_id=_project_id(current), bundle_id=body.bundle_id, dry_run=body.dry_run
    )
    return R.ok(result)
