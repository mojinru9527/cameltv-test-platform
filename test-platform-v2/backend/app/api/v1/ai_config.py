"""AI 配置 API —— /api/v1/ai-config/*（项目级提供方池）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services.ai_config_service import ai_config_service

router = APIRouter(prefix="/ai-config", tags=["AI 配置"])


class ProviderIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = "openai_compatible"
    api_base_url: str = ""
    api_key: str = ""
    models: list[str] = []
    default_model: str = ""
    is_default: bool = False
    enabled: bool = True


class ProviderUpdateIn(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    models: list[str] | None = None
    default_model: str | None = None
    is_default: bool | None = None
    enabled: bool | None = None


@router.get("/providers", response_model=R[list], summary="项目 AI 提供方列表")
def list_providers(
    current: CurrentUser = Depends(require_permission("ai_config:view")),
    db: Session = Depends(get_db),
):
    return R.ok(ai_config_service.list_providers(db, current.project_id or 0))


@router.post("/providers", response_model=R[dict], summary="新建 AI 提供方")
def create_provider(
    body: ProviderIn,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    row = ai_config_service.create_provider(
        db, current.project_id or 0, body.model_dump()
    )
    return R.ok({"id": row.id})


@router.put(
    "/providers/{provider_id}", response_model=R[dict], summary="更新 AI 提供方"
)
def update_provider(
    provider_id: int,
    body: ProviderUpdateIn,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    row = ai_config_service.update_provider(
        db, current.project_id or 0, provider_id, body.model_dump(exclude_none=True)
    )
    return R.ok({"id": row.id})


@router.delete(
    "/providers/{provider_id}", response_model=R[dict], summary="删除 AI 提供方"
)
def delete_provider(
    provider_id: int,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    ai_config_service.delete_provider(db, current.project_id or 0, provider_id)
    return R.ok({"deleted": provider_id})


@router.post(
    "/providers/{provider_id}/test-connection",
    response_model=R[dict],
    summary="测试提供方连通性",
)
def test_connection(
    provider_id: int,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    return R.ok(
        ai_config_service.test_connection(db, current.project_id or 0, provider_id)
    )


@router.get("/resolve", response_model=R[dict], summary="当前项目生效 AI 配置")
def resolve_config(
    current: CurrentUser = Depends(require_permission("ai_config:view")),
    db: Session = Depends(get_db),
):
    return R.ok(ai_config_service.resolve_out(db, current.project_id or 0))
