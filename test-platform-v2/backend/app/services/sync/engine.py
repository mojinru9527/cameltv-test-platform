"""SyncEngine — orchestration layer for external defect sync operations."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.sync_log import SyncLog
from app.services.sync.base import BaseSyncProvider

logger = logging.getLogger(__name__)


def get_provider(provider_type: str, config: dict) -> BaseSyncProvider:
    """Factory: return the correct provider instance for the given type."""
    if provider_type == "jira":
        from app.services.sync.jira import JiraSyncProvider
        return JiraSyncProvider(config)
    elif provider_type == "tapd":
        from app.services.sync.tapd import TapdSyncProvider
        return TapdSyncProvider(config)
    else:
        raise ValueError(f"Unknown provider_type: {provider_type}")


def push_defect(db: Session, integration_id: int, defect_id: int, project_id: int) -> dict:
    """Push a single defect to the external system.
    On success, updates defect.external_id and defect.external_url.
    Returns sync_log as dict.
    """
    from app.models.integration import IntegrationConfig
    from app.models.defect import Defect
    from app.core.cipher import decrypt_value

    integration = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    if not integration:
        return _log_skip(db, integration_id, defect_id, "push", "Integration config not found")

    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        return _log_skip(db, integration_id, defect_id, "push", "Defect not found")

    try:
        auth = json.loads(decrypt_value(integration.auth_json))
    except Exception:
        auth = {}

    provider = get_provider(integration.provider_type, {
        "base_url": integration.base_url,
        "auth": auth,
        "field_mapping": integration.field_mapping,
    })

    defect_dict = {
        "title": defect.title,
        "description": defect.description,
        "severity": defect.severity,
        "status": defect.status,
    }

    import asyncio
    try:
        success, external_id, external_url = asyncio.run(provider.push_defect(defect_dict))
    except Exception as e:
        logger.exception("Error pushing defect %d to %s", defect_id, integration.provider_type)
        return _log_fail(db, integration_id, defect_id, "push", str(e))

    if success and external_id:
        defect.external_id = external_id
        defect.external_url = external_url
        defect.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _log_success(db, integration_id, defect_id, "push", external_id, f"Pushed to {integration.provider_type}: {external_id}")
    else:
        return _log_fail(db, integration_id, defect_id, "push", external_url or "Push failed")


def pull_defect_status(db: Session, integration_id: int, defect_id: int, project_id: int) -> dict:
    """Pull latest status from external system for a linked defect.
    Uses last-write-wins conflict resolution.
    Returns sync_log as dict.
    """
    from app.models.integration import IntegrationConfig
    from app.models.defect import Defect
    from app.core.cipher import decrypt_value

    integration = db.query(IntegrationConfig).filter(
        IntegrationConfig.id == integration_id,
        IntegrationConfig.project_id == project_id,
    ).first()
    if not integration:
        return _log_skip(db, integration_id, defect_id, "pull", "Integration config not found")

    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        return _log_skip(db, integration_id, defect_id, "pull", "Defect not found")

    if not defect.external_id:
        return _log_skip(db, integration_id, defect_id, "pull", "Defect has no external_id — push first")

    try:
        auth = json.loads(decrypt_value(integration.auth_json))
    except Exception:
        auth = {}

    provider = get_provider(integration.provider_type, {
        "base_url": integration.base_url,
        "auth": auth,
        "field_mapping": integration.field_mapping,
    })

    import asyncio
    try:
        success, remote_data, error = asyncio.run(provider.pull_defect(defect.external_id))
    except Exception as e:
        logger.exception("Error pulling defect %d from %s", defect_id, integration.provider_type)
        return _log_fail(db, integration_id, defect_id, "pull", str(e))

    if not success or not remote_data:
        return _log_fail(db, integration_id, defect_id, "pull", error or "Pull failed")

    # Conflict resolution: last-write-wins
    remote_updated_str = remote_data.get("updated", "")
    try:
        remote_updated = datetime.fromisoformat(remote_updated_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        remote_updated = None

    local_updated = defect.updated_at

    if remote_updated and local_updated and local_updated > remote_updated:
        return _log_skip(db, integration_id, defect_id, "pull",
                         f"Local version is newer (local: {local_updated.isoformat()}, remote: {remote_updated.isoformat()})")

    # Apply remote changes
    changed = False
    if remote_data.get("status") and remote_data["status"] != defect.status:
        defect.status = remote_data["status"]
        changed = True
    if remote_data.get("severity") and remote_data["severity"] != defect.severity:
        defect.severity = remote_data["severity"]
        changed = True

    if changed:
        defect.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _log_success(db, integration_id, defect_id, "pull", defect.external_id,
                            f"Updated from {integration.provider_type}: status={defect.status}")
    else:
        return _log_skip(db, integration_id, defect_id, "pull",
                         f"No changes from {integration.provider_type} (status already {defect.status})")


def run_scheduled_sync(integration_id: int) -> dict:
    """Entry point for APScheduler. Opens its own DB session.
    Pushes all unlinked defects, then pulls status for all linked defects.
    """
    from app.core.db import SessionLocal
    from app.models.integration import IntegrationConfig
    from app.models.defect import Defect

    db = SessionLocal()
    pushed = 0
    pulled = 0
    errors = 0

    try:
        integration = db.query(IntegrationConfig).filter(IntegrationConfig.id == integration_id).first()
        if not integration or not integration.enabled:
            return {"pushed": 0, "pulled": 0, "errors": 0, "message": "Integration disabled or not found"}

        # Push: all defects without external_id
        if integration.sync_direction in ("bidirectional", "push_only"):
            unlinked = db.query(Defect).filter(
                Defect.project_id == integration.project_id,
                Defect.external_id == "",
            ).all()
            for d in unlinked:
                try:
                    push_defect(db, integration_id, d.id, integration.project_id)
                    pushed += 1
                except Exception as e:
                    logger.error("Scheduled push failed for defect %d: %s", d.id, e)
                    errors += 1

        # Pull: all linked defects
        if integration.sync_direction in ("bidirectional", "pull_only"):
            linked = db.query(Defect).filter(
                Defect.project_id == integration.project_id,
                Defect.external_id != "",
            ).all()
            for d in linked:
                try:
                    pull_defect_status(db, integration_id, d.id, integration.project_id)
                    pulled += 1
                except Exception as e:
                    logger.error("Scheduled pull failed for defect %d: %s", d.id, e)
                    errors += 1

        logger.info("Scheduled sync for integration %d: pushed=%d, pulled=%d, errors=%d",
                    integration_id, pushed, pulled, errors)
        return {"pushed": pushed, "pulled": pulled, "errors": errors, "message": "Sync complete"}
    finally:
        db.close()


# ── Internal log helpers ──

def _write_log(db: Session, integration_id: int, defect_id: int, direction: str,
               status: str, external_id: str, message: str) -> dict:
    entry = SyncLog(
        integration_id=integration_id,
        defect_id=defect_id,
        direction=direction,
        status=status,
        external_id=external_id,
        message=message,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _log_to_dict(entry)


def _log_success(db, iid, did, d, eid, msg) -> dict:
    return _write_log(db, iid, did, d, "success", eid, msg)


def _log_fail(db, iid, did, d, msg) -> dict:
    return _write_log(db, iid, did, d, "failed", "", msg)


def _log_skip(db, iid, did, d, msg) -> dict:
    return _write_log(db, iid, did, d, "skipped", "", msg)


def _log_to_dict(entry: SyncLog) -> dict:
    return {
        "id": entry.id,
        "integration_id": entry.integration_id,
        "defect_id": entry.defect_id,
        "direction": entry.direction,
        "status": entry.status,
        "external_id": entry.external_id,
        "message": entry.message,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }
