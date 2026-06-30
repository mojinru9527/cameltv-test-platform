"""API Token management (project-level)."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_project
from app.models.api_token import ApiToken
from app.schemas.common import R

router = APIRouter(prefix="/tokens", tags=["API Token"])


@router.get("", response_model=R[list], summary="API Token 列表")
def list_tokens(
    current: CurrentUser = Depends(require_project),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(ApiToken).where(ApiToken.project_id == current.project_id)
    ).all()
    return R.ok([{
        "id": t.id, "name": t.name, "token_prefix": t.token_prefix,
        "scopes": t.scopes, "enabled": t.enabled,
        "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    } for t in rows])


@router.post("", response_model=R[dict], summary="创建 API Token")
def create_token(
    body: dict,
    current: CurrentUser = Depends(require_project),
    db: Session = Depends(get_db),
):
    plain, token_hash = ApiToken.generate()
    t = ApiToken(
        project_id=current.project_id,
        name=body.get("name", "CI Token"),
        token_hash=token_hash,
        token_prefix=plain[:12],
        scopes=str(body.get("scopes", ["trigger"])),
        enabled=True,
    )
    db.add(t)
    db.commit()
    # Only time the plain token is returned!
    return R.ok({
        "id": t.id,
        "name": t.name,
        "token": plain,   # ⚠️ save this now — we don't store the plain value
        "token_prefix": t.token_prefix,
        "scopes": t.scopes,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    })


@router.put("/{token_id}", response_model=R[dict], summary="更新 API Token")
def update_token(
    token_id: int,
    body: dict,
    current: CurrentUser = Depends(require_project),
    db: Session = Depends(get_db),
):
    t = db.scalar(
        select(ApiToken).where(
            ApiToken.id == token_id, ApiToken.project_id == current.project_id
        )
    )
    if not t:
        from app.core.exceptions import not_found
        raise not_found("API Token")

    if "name" in body:
        t.name = body["name"]
    if "enabled" in body:
        t.enabled = body["enabled"]

    db.commit()
    return R.ok({"id": t.id, "name": t.name, "enabled": t.enabled})


@router.delete("/{token_id}", response_model=R[dict], summary="删除 API Token")
def delete_token(
    token_id: int,
    current: CurrentUser = Depends(require_project),
    db: Session = Depends(get_db),
):
    t = db.scalar(
        select(ApiToken).where(
            ApiToken.id == token_id, ApiToken.project_id == current.project_id
        )
    )
    if not t:
        from app.core.exceptions import not_found
        raise not_found("API Token")
    db.delete(t)
    db.commit()
    return R.ok({"deleted": True})
