"""EnvironmentSnapshotService (V31-001/V31-005).

Every ExecutionRun must bind an EnvironmentSnapshot. When auto-detection cannot
resolve the build, the tester provides a ``build_label`` but we always compute a
stable ``fingerprint_hash`` so the Run is still bound to a concrete environment.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.environment.fingerprint import (
    compute_fingerprint_hash,
    confidence_from_components,
)
from app.modules.aitde.execution import repository
from app.modules.aitde.execution.models import EnvironmentSnapshot


def capture_snapshot(
    db: Session,
    environment_id: int,
    mission_id: int,
    project_id: int,
    data: dict[str, Any],
) -> EnvironmentSnapshot:
    if not environment_id:
        raise APIException(code=400, msg="环境不能为空", http_status=400)

    service_versions = data.get("service_versions") or {}
    fingerprint_hash = compute_fingerprint_hash(
        service_versions=service_versions,
        openapi_hash=data.get("openapi_hash"),
        db_schema_version=data.get("db_schema_version"),
        config_hash=data.get("config_hash"),
        static_asset_hash=data.get("static_asset_hash"),
        frontend_version=data.get("frontend_version"),
        build_label=data.get("build_label"),
    )
    row = repository.create_snapshot(
        db,
        {
            "build_label": data.get("build_label"),
            "frontend_version": data.get("frontend_version"),
            "service_versions_json": json.dumps(
                service_versions, sort_keys=True, ensure_ascii=False
            ),
            "openapi_hash": data.get("openapi_hash"),
            "db_schema_version": data.get("db_schema_version"),
            "config_hash": data.get("config_hash"),
            "static_asset_hash": data.get("static_asset_hash"),
            "manual_note": data.get("manual_note"),
            "fingerprint_hash": fingerprint_hash,
            "created_by_type": "AUTO" if not data.get("build_label") else "MANUAL",
            "confidence": confidence_from_components(data),
        },
        environment_id=environment_id,
        mission_id=mission_id,
    )
    return row


def get_snapshot(db: Session, snapshot_id: int, project_id: int) -> EnvironmentSnapshot:
    row = repository.get_snapshot(db, snapshot_id, project_id)
    if not row:
        raise APIException(code=404, msg="环境快照不存在", http_status=404)
    return row


def latest_snapshot(
    db: Session, environment_id: int, mission_id: int
) -> EnvironmentSnapshot | None:
    return repository.latest_snapshot(db, environment_id, mission_id)
