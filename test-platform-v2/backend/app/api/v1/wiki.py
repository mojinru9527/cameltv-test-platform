"""LLM-Wiki 知识库 API 路由 —— /api/v1/wiki/*

VNext-1..3：蓝湖导入 → Raw Source → Wiki 编译 → RAG vs Wiki 差异对比 → 待审产物。
所有能力受配置开关门禁（默认 OFF，raise APIException(503)）与 RBAC（wiki:*）保护。

本文件在切片 0 仅暴露 GET /wiki/config（读开关）；切片 1..3 逐步补齐导入/页面/差异端点。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.schemas.wiki import WikiConfigOut

router = APIRouter(prefix="/wiki", tags=["Wiki 知识库"])


@router.get("/config", response_model=R[WikiConfigOut], summary="Wiki 能力开关")
def get_wiki_config(
    current: CurrentUser = Depends(require_permission("wiki:view")),
    db: Session = Depends(get_db),
):
    return R.ok(WikiConfigOut(
        wiki_enabled=settings.wiki_enabled,
        wiki_auto_ingest_enabled=settings.wiki_auto_ingest_enabled,
        wiki_diff_enabled=settings.wiki_diff_enabled,
        wiki_auto_create_artifact=settings.wiki_auto_create_artifact,
        lanhu_mcp_enabled=settings.lanhu_mcp_enabled,
    ))
