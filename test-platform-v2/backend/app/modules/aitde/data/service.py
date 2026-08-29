"""AITDE V3.2 DataSource service (V32-001).

Creates / lists / reads typed data sources with a conservative write policy:

* A data source targeting a **production environment** may only be created
  ``READONLY`` — a ``READWRITE`` data source against production is rejected.
* The secret value is never stored or serialized; only ``secret_ref`` (the
  reference) is persisted and returned.
* ``PROD_TEMPLATE`` is a reserved enum only in V3.2 and is rejected on create.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.environment import Environment
from app.modules.aitde.common.enums import (
    DataSourceAccessMode,
    DataSourceStatus,
    DataSourceType,
)
from app.modules.aitde.data import repository
from app.modules.aitde.data.models import DataSource
from app.modules.aitde.data.schemas import DataSourceCreate

_SOURCE_TYPES = {st.value for st in DataSourceType}
# Reserved-only in V3.2 (deferred to V3.6); never created this version.
_RESERVED_TYPES = {DataSourceType.PROD_TEMPLATE.value}

# Config keys that must never carry a secret: secrets are referenced through
# secret_ref into an external store. Exact (case-insensitive) key match only,
# so a header named e.g. "X-Token" is not falsely rejected.
_SECRET_CONFIG_KEYS = {
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "credential",
    "authorization",
    "client_secret",
}


def _find_secret_key(obj: Any) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in _SECRET_CONFIG_KEYS:
                return str(k)
            found = _find_secret_key(v)
            if found:
                return found
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found = _find_secret_key(item)
            if found:
                return found
    return None


def _redact_config(config_json: str) -> str:
    """Defense-in-depth read redaction of any sensitive config key values."""
    try:
        config = json.loads(config_json or "{}")
    except (ValueError, TypeError):
        return config_json or "{}"

    def _redact(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                k: ("<REDACTED>" if str(k).lower() in _SECRET_CONFIG_KEYS else _redact(v))
                for k, v in node.items()
            }
        if isinstance(node, (list, tuple)):
            return [_redact(v) for v in node]
        return node

    return json.dumps(_redact(config), ensure_ascii=False)


def _is_prod_environment(db: Session, environment_id: int | None) -> bool:
    if environment_id is None:
        return False
    env = db.get(Environment, environment_id)
    if env is None:
        return False
    return env.env_type == "prod" or env.is_production


def create_data_source(
    db: Session, payload: DataSourceCreate, project_id: int, user_id: int
) -> DataSource:
    stype = payload.source_type.value
    if stype not in _SOURCE_TYPES:
        raise APIException(code=400, msg=f"不支持的数据源类型：{stype}", http_status=400)
    if stype in _RESERVED_TYPES:
        raise APIException(
            code=400, msg=f"数据源类型 {stype} 暂不开放（预留模板）", http_status=400
        )

    access_mode = payload.access_mode.value
    if payload.environment_id is not None and _is_prod_environment(
        db, payload.environment_id
    ):
        if access_mode == DataSourceAccessMode.READWRITE.value:
            raise APIException(
                code=400,
                msg="生产环境数据源仅允许只读（READONLY），禁止 READWRITE 创建",
                http_status=400,
            )

    # Secrets must never be embedded in config_json; only secret_ref is stored.
    config = payload.config or {}
    offending = _find_secret_key(config)
    if offending:
        raise APIException(
            code=400,
            msg=f"config 中禁止包含敏感字段：{offending}，请改用 secret_ref 引用密钥",
            http_status=400,
        )

    data: dict[str, Any] = {
        "environment_id": payload.environment_id,
        "source_type": stype,
        "name": payload.name,
        "network_zone": payload.network_zone,
        "secret_ref": payload.secret_ref,
        "access_mode": access_mode,
        "config_json": json.dumps(config, ensure_ascii=False),
        "policy_ref": payload.policy_ref,
        "status": DataSourceStatus.ACTIVE.value,
    }
    row = repository.create_data_source(db, data, project_id, user_id)
    db.commit()
    db.refresh(row)
    return row


def get_data_source(db: Session, data_source_id: int, project_id: int) -> DataSource:
    row = repository.get_data_source(db, data_source_id, project_id)
    if not row:
        raise APIException(code=404, msg="数据源不存在", http_status=404)
    return row


def list_data_sources(db: Session, project_id: int) -> list[DataSource]:
    return repository.list_data_sources(db, project_id)


def to_dict(row: DataSource) -> dict[str, Any]:
    """Serialize a DataSource without ever exposing the referenced secret value.

    Only ``secret_ref`` (the reference) is carried; the secret it points at is
    never read into this dict.
    """
    return {
        "id": row.id,
        "project_id": row.project_id,
        "environment_id": row.environment_id,
        "source_type": row.source_type,
        "name": row.name,
        "network_zone": row.network_zone,
        "secret_ref": row.secret_ref,
        "access_mode": row.access_mode,
        "config_json": _redact_config(row.config_json),
        "policy_ref": row.policy_ref,
        "status": row.status,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
