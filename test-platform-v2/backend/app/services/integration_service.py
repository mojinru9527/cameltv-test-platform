"""Integration config service — CRUD + test_connection."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.cipher import encrypt_value, decrypt_value
from app.models.integration import IntegrationConfig
from app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)

MASKED = "********"


def list_integrations(db: Session, project_id: int) -> list[dict]:
    rows = db.query(IntegrationConfig).filter(
        IntegrationConfig.project_id == project_id,
    ).order_by(IntegrationConfig.created_at.desc()).all()
    return [_row_to_dict(r, mask_auth=True) for r in rows]


def get_integration(db: Session, integration_id: int, project_id: int) -> dict | None:
    row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    return _row_to_dict(row, mask_auth=True) if row else None


def create_integration(db: Session, data: dict, project_id: int) -> dict:
    encrypted = encrypt_value(data.get("auth_json", "{}"))
    row = IntegrationConfig(
        project_id=project_id,
        name=data.get("name", ""),
        provider_type=data.get("provider_type", "jira"),
        base_url=data.get("base_url", ""),
        auth_json=encrypted,
        field_mapping=data.get("field_mapping", "{}"),
        sync_direction=data.get("sync_direction", "bidirectional"),
        sync_interval_minutes=data.get("sync_interval_minutes", 0),
        enabled=data.get("enabled", True),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row, mask_auth=True)


def update_integration(db: Session, integration_id: int, data: dict, project_id: int) -> dict | None:
    row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    if not row:
        return None

    for field in ("name", "base_url", "field_mapping", "sync_direction"):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    if "provider_type" in data and data["provider_type"] is not None:
        row.provider_type = data["provider_type"]
    if "sync_interval_minutes" in data and data["sync_interval_minutes"] is not None:
        row.sync_interval_minutes = data["sync_interval_minutes"]
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = data["enabled"]
    if "auth_json" in data and data["auth_json"] is not None and data["auth_json"] != MASKED:
        row.auth_json = encrypt_value(data["auth_json"])

    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row, mask_auth=True)


def delete_integration(db: Session, integration_id: int, project_id: int) -> bool:
    row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def test_connection(provider_type: str, base_url: str, auth_json_plain: str) -> dict:
    """Test connection with given credentials. Does NOT save anything."""
    try:
        auth = json.loads(auth_json_plain) if isinstance(auth_json_plain, str) else auth_json_plain
    except json.JSONDecodeError:
        return {"success": False, "message": "auth_json is not valid JSON"}

    from app.services.sync.engine import get_provider
    config = {"base_url": base_url, "auth": auth, "field_mapping": {}}

    import asyncio
    try:
        provider = get_provider(provider_type, config)
        success, message = asyncio.run(provider.test_connection())
        return {"success": success, "message": message}
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {e}"}


def get_decrypted_auth(db: Session, integration_id: int, project_id: int) -> tuple[dict, str] | None:
    """Returns (config_dict, provider_type) with decrypted auth. Internal use only — NOT exposed via API."""
    row = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    if not row:
        return None
    try:
        auth = json.loads(decrypt_value(row.auth_json))
    except Exception:
        auth = {}
    return {
        "base_url": row.base_url,
        "auth": auth,
        "field_mapping": row.field_mapping,
    }, row.provider_type


def list_sync_logs(db: Session, integration_id: int, page: int = 1, page_size: int = 20) -> dict:
    query = db.query(SyncLog).filter(SyncLog.integration_id == integration_id)
    total = query.count()
    rows = query.order_by(SyncLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_sync_log_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ── Internal helpers ──

def _row_to_dict(row: IntegrationConfig, mask_auth: bool = True) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "name": row.name,
        "provider_type": row.provider_type,
        "base_url": row.base_url,
        "auth_json": MASKED if mask_auth else row.auth_json,
        "field_mapping": row.field_mapping,
        "sync_direction": row.sync_direction,
        "sync_interval_minutes": row.sync_interval_minutes,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _sync_log_to_dict(row: SyncLog) -> dict:
    return {
        "id": row.id,
        "integration_id": row.integration_id,
        "defect_id": row.defect_id,
        "direction": row.direction,
        "status": row.status,
        "external_id": row.external_id,
        "message": row.message,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
