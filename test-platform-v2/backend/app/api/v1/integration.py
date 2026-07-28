"""Integration config API routes — external system sync configuration."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_permission
from app.schemas.common import R
from app.schemas.integration import (
    IntegrationConfigCreate,
    IntegrationConfigOut,
    IntegrationConfigUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.services import integration_service
from app.services.audit_service import write_audit

logger = logging.getLogger("integration")
router = APIRouter(prefix="/integrations", tags=["集成配置"])


def _audit(req: Request, cu: CurrentUser, db: Session, action: str, target: str, detail: str = ""):
    write_audit(
        db,
        user_id=cu.user.id,
        username=cu.user.username or "",
        project_id=cu.project_id or 0,
        action=action,
        target=target,
        detail=detail,
        ip=req.client.host if req.client else "",
    )


# ── Config CRUD ──

@router.get("", response_model=R[dict])
def list_integrations(
    current: CurrentUser = Depends(require_permission("integration:list")),
    db: Session = Depends(get_db),
):
    items = integration_service.list_integrations(db, current.project_id or 0)
    return R.ok({"items": items, "total": len(items)})


@router.post("", response_model=R[IntegrationConfigOut])
def create_integration(
    req: Request,
    body: IntegrationConfigCreate,
    current: CurrentUser = Depends(require_permission("integration:manage")),
    db: Session = Depends(get_db),
):
    r = integration_service.create_integration(db, body.model_dump(), current.project_id or 0)
    _audit(req, current, db, "integration:create", f"#{r['id']} {r['name']}")
    return R.ok(IntegrationConfigOut(**r))


@router.get("/{integration_id}", response_model=R[IntegrationConfigOut])
def get_integration(
    integration_id: int,
    current: CurrentUser = Depends(require_permission("integration:list")),
    db: Session = Depends(get_db),
):
    r = integration_service.get_integration(db, integration_id, current.project_id or 0)
    if not r:
        from app.core.exceptions import not_found
        raise not_found("集成配置")
    return R.ok(IntegrationConfigOut(**r))


@router.put("/{integration_id}", response_model=R[IntegrationConfigOut])
def update_integration(
    req: Request,
    integration_id: int,
    body: IntegrationConfigUpdate,
    current: CurrentUser = Depends(require_permission("integration:manage")),
    db: Session = Depends(get_db),
):
    r = integration_service.update_integration(
        db, integration_id, body.model_dump(exclude_none=True), current.project_id or 0
    )
    if not r:
        from app.core.exceptions import not_found
        raise not_found("集成配置")
    _audit(req, current, db, "integration:update", f"#{r['id']} {r['name']}")
    return R.ok(IntegrationConfigOut(**r))


@router.delete("/{integration_id}", response_model=R[dict])
def delete_integration(
    req: Request,
    integration_id: int,
    current: CurrentUser = Depends(require_permission("integration:manage")),
    db: Session = Depends(get_db),
):
    ok = integration_service.delete_integration(db, integration_id, current.project_id or 0)
    if not ok:
        from app.core.exceptions import not_found
        raise not_found("集成配置")
    _audit(req, current, db, "integration:delete", f"#{integration_id}")
    return R.ok({"deleted": True})


# ── Test connection (no save) ──

@router.post("/test-connection", response_model=R[TestConnectionResponse])
def test_connection(
    body: TestConnectionRequest,
    current: CurrentUser = Depends(require_permission("integration:manage")),
):
    result = integration_service.test_connection(body.provider_type, body.base_url, body.auth_json)
    return R.ok(TestConnectionResponse(**result))


# ── Manual sync trigger ──

@router.post("/{integration_id}/sync-now", response_model=R[dict])
def sync_now(
    integration_id: int,
    direction: str | None = Query(None, description="push | pull | bidirectional (default uses config setting)"),
    current: CurrentUser = Depends(require_permission("integration:sync")),
    db: Session = Depends(get_db),
):
    from app.services.sync import engine as sync_engine
    from app.models.defect import Defect

    cfg = integration_service.get_integration(db, integration_id, current.project_id or 0)
    if not cfg:
        from app.core.exceptions import not_found
        raise not_found("集成配置")

    if direction is None:
        direction = cfg["sync_direction"]

    pushed = 0
    pulled = 0
    errors = 0

    if direction in ("bidirectional", "push_only"):
        unlinked = db.query(Defect).filter(
            Defect.project_id == current.project_id,
            Defect.external_id == "",
        ).all()
        for d in unlinked:
            try:
                sync_engine.push_defect(db, integration_id, d.id, current.project_id or 0)
                pushed += 1
            except Exception as e:
                logger.error("Sync push failed for defect %d: %s", d.id, e)
                errors += 1

    if direction in ("bidirectional", "pull_only"):
        linked = db.query(Defect).filter(
            Defect.project_id == current.project_id,
            Defect.external_id != "",
        ).all()
        for d in linked:
            try:
                sync_engine.pull_defect_status(db, integration_id, d.id, current.project_id or 0)
                pulled += 1
            except Exception as e:
                logger.error("Sync pull failed for defect %d: %s", d.id, e)
                errors += 1

    return R.ok({"pushed": pushed, "pulled": pulled, "errors": errors, "message": "Sync complete"})


# ── Sync logs ──

@router.get("/{integration_id}/sync-logs", response_model=R[dict])
def list_sync_logs(
    integration_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: CurrentUser = Depends(require_permission("integration:list")),
    db: Session = Depends(get_db),
):
    result = integration_service.list_sync_logs(db, integration_id, page, page_size)
    return R.ok(result)
