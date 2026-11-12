"""AIQE Console 管理 API（P1）：质量门禁、噪音规则、Profile、Artifact GC。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.aiqe.services.artifact_gc import purge_expired_artifacts
from app.aiqe.services.noise_rule_service import (
    NoiseRuleError,
    create_rule,
    delete_rule,
    is_effective,
    list_rules,
    renew_rule,
    update_rule,
)
from app.aiqe.services.profile_service import (
    ProfileError,
    approve_profile,
    create_profile,
    list_profiles,
    update_config,
)
from app.aiqe.services.quality_gate import evaluate_stats
from app.core.deps import CurrentUser, get_db, require_permission
from app.core.exceptions import APIException
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


class NoiseRulePatchIn(BaseModel):
    pattern: str | None = None
    action: str | None = None
    expires_at: datetime | None = None


def _noise_rule_out(row) -> dict:
    return {
        "id": row.id,
        "pattern": row.pattern,
        "action": row.action,
        "scope": row.scope,
        "expires_at": row.expires_at,
        "status": row.status,
        "effective": is_effective(row),
    }


class ProfileIn(BaseModel):
    name: str
    purpose: str = "core_isolated"
    config: dict = {}


class ProfileConfigIn(BaseModel):
    config: dict


def _profile_out(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "purpose": row.purpose,
        "version": row.version,
        "approval_status": row.approval_status,
        "checksum": row.checksum,
        "owner_id": row.owner_id,
        "frozen": row.approval_status == "approved",
    }


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
    return R.ok([_noise_rule_out(row) for row in rows])


@router.post("/noise-rules", response_model=R[dict], summary="创建噪音规则")
def post_noise_rule(
    body: NoiseRuleIn,
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = create_rule(
            db,
            project_id=current.project_id or 0,
            pattern=body.pattern,
            action=body.action,
            scope=body.scope,
            expires_at=body.expires_at,
            created_by=current.user.id,
        )
    except NoiseRuleError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    return R.ok(_noise_rule_out(row))


@router.patch("/noise-rules/{rule_id}", response_model=R[dict], summary="更新噪音规则")
def patch_noise_rule(
    rule_id: int,
    body: NoiseRulePatchIn,
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = update_rule(
            db,
            rule_id,
            pattern=body.pattern,
            action=body.action,
            expires_at=body.expires_at,
        )
    except NoiseRuleError as exc:
        message = str(exc)
        status = 404 if "不存在" in message else 400
        raise APIException(code=status, msg=message, http_status=status) from None
    return R.ok(_noise_rule_out(row))


@router.post("/noise-rules/{rule_id}/renew", response_model=R[dict], summary="续期噪音规则")
def post_renew_rule(
    rule_id: int,
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = renew_rule(db, rule_id)
    except NoiseRuleError as exc:
        raise APIException(code=404, msg=str(exc), http_status=404) from None
    return R.ok(_noise_rule_out(row))


@router.delete("/noise-rules/{rule_id}", response_model=R[dict], summary="删除噪音规则")
def remove_noise_rule(
    rule_id: int,
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        delete_rule(db, rule_id)
    except NoiseRuleError as exc:
        raise APIException(code=404, msg=str(exc), http_status=404) from None
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
    rows = list_profiles(db, current.project_id or 0)
    return R.ok([_profile_out(row) for row in rows])


@router.post("/profiles", response_model=R[dict], summary="创建 Execution Profile")
def post_profile(
    body: ProfileIn,
    _console: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = create_profile(
            db,
            project_id=current.project_id or 0,
            name=body.name,
            purpose=body.purpose,
            config=body.config,
            owner_id=current.user.id,
        )
    except ProfileError as exc:
        raise APIException(code=400, msg=str(exc), http_status=400) from None
    return R.ok(_profile_out(row))


@router.post("/profiles/{profile_id}/approve", response_model=R[dict], summary="审批 Execution Profile（approved 冻结）")
def post_approve_profile(
    profile_id: str,
    _console: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = approve_profile(db, profile_id)
    except ProfileError as exc:
        raise APIException(code=404, msg=str(exc), http_status=404) from None
    return R.ok(_profile_out(row))


@router.patch("/profiles/{profile_id}", response_model=R[dict], summary="更新 Execution Profile 配置")
def patch_profile(
    profile_id: str,
    body: ProfileConfigIn,
    _console: CurrentUser = Depends(require_permission("menu:aiqe_runs")),
    _current: CurrentUser = Depends(require_permission("defect:update")),
    db: Session = Depends(get_db),
):
    try:
        row = update_config(db, profile_id, body.config)
    except ProfileError as exc:
        message = str(exc)
        status = 409 if "approved" in message else 404
        raise APIException(code=status, msg=message, http_status=status) from None
    return R.ok(_profile_out(row))
