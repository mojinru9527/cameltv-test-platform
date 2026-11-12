"""AIQE Console 管理 API（P1）：质量门禁、噪音规则、Profile、Artifact GC。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.profile import ExecutionProfile
from app.aiqe.services.artifact_gc import purge_expired_artifacts
from app.aiqe.services.noise_rule_service import (
    create_rule,
    delete_rule,
    list_rules,
    renew_rule,
)
from app.aiqe.services.quality_gate import evaluate_stats
from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import R

router = APIRouter(prefix="/aiqe/admin", tags=["AIQE 管理"])


class QualityGateIn(BaseModel):
    p0_total: int = 0
    p0_passed: int = 0
    p0_failed: int = 0
    p0_unknown: int = 0
    p0_not_run: int = 0


class NoiseRuleIn(BaseModel):
    pattern: str
    action: str = "suppress"
    scope: str = "run"
    expires_at: datetime | None = None


@router.post("/quality-gate", response_model=R[dict], summary="质量门禁判定")
def quality_gate(
    body: QualityGateIn,
    _current: CurrentUser = Depends(require_permission("defect:list")),
):
    return R.ok(evaluate_stats(body.model_dump()))


@router.get("/noise-rules", response_model=R[list], summary="噪音规则列表")
def get_noise_rules(
    include_expired: bool = Query(default=True),
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list_rules(db, current.project_id or 0, include_expired=include_expired)
    return R.ok(
        [
            {
                "id": row.id,
                "pattern": row.pattern,
                "action": row.action,
                "scope": row.scope,
                "expires_at": row.expires_at,
                "status": row.status,
            }
            for row in rows
        ]
    )


@router.post("/noise-rules", response_model=R[dict], summary="创建噪音规则")
def post_noise_rule(
    body: NoiseRuleIn,
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    row = create_rule(
        db,
        project_id=current.project_id or 0,
        pattern=body.pattern,
        action=body.action,
        scope=body.scope,
        expires_at=body.expires_at,
    )
    return R.ok({"id": row.id, "expires_at": row.expires_at, "status": row.status})


@router.post("/noise-rules/{rule_id}/renew", response_model=R[dict], summary="续期噪音规则")
def post_renew_rule(
    rule_id: int,
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    row = renew_rule(db, rule_id)
    return R.ok({"id": row.id, "expires_at": row.expires_at, "status": row.status})


@router.delete("/noise-rules/{rule_id}", response_model=R[dict], summary="删除噪音规则")
def remove_noise_rule(
    rule_id: int,
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    delete_rule(db, rule_id)
    return R.ok({"id": rule_id, "deleted": True})


@router.post("/artifacts/gc", response_model=R[dict], summary="Artifact 留存清理")
def run_artifact_gc(
    retention_days: int = Query(default=30, ge=1),
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    return R.ok(purge_expired_artifacts(db, retention_days=retention_days))


@router.get("/profiles", response_model=R[list], summary="Execution Profile 列表")
def get_profiles(
    current: CurrentUser = Depends(require_permission("defect:list")),
    db: Session = Depends(get_db),
):
    rows = list(
        db.scalars(
            select(ExecutionProfile)
            .where(ExecutionProfile.project_id == (current.project_id or 0))
            .order_by(ExecutionProfile.created_at.desc())
        )
    )
    return R.ok(
        [
            {
                "id": row.id,
                "name": row.name,
                "purpose": row.purpose,
                "version": row.version,
                "approval_status": row.approval_status,
                "checksum": row.checksum,
            }
            for row in rows
        ]
    )
