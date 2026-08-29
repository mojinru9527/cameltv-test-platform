"""ScenarioAdapterService (V31-001).

Binds a ScenarioVersion to an existing API/UI asset or a future Runtime Adapter.
The adapter/version semantic is stable: a bind is unique per
(scenario_version_id, adapter_type, adapter_version).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import AdapterStatus, AdapterType
from app.modules.aitde.execution import repository
from app.modules.aitde.execution.models import ScenarioAdapter

_VALID_TYPES = {t.value for t in AdapterType}
_VALID_STATUSES = {s.value for s in AdapterStatus}


def create_adapter(
    db: Session,
    scenario_id: int,
    data: dict[str, Any],
    project_id: int,
    user_id: int,
) -> ScenarioAdapter:
    adapter_type = (data.get("adapter_type") or AdapterType.API.value)
    if adapter_type not in _VALID_TYPES:
        raise APIException(code=400, msg=f"非法适配器类型：{adapter_type}", http_status=400)

    scenario_version_id = data.get("scenario_version_id")
    if not scenario_version_id:
        raise APIException(code=400, msg="scenario_version_id 不能为空", http_status=400)

    try:
        repository.validate_adapter_bind(db, scenario_id, int(scenario_version_id), project_id)
    except ValueError as exc:
        message = (
            "场景版本不属于当前项目"
            if str(exc) == "SCENARIO_NOT_IN_PROJECT"
            else "场景与场景版本不匹配"
        )
        raise APIException(code=400, msg=message, http_status=400) from exc

    try:
        return repository.create_adapter(
            db,
            {
                "scenario_id": scenario_id,
                "scenario_version_id": int(scenario_version_id),
                "adapter_type": adapter_type,
                "status": AdapterStatus.DRAFT.value,
                "source_asset_type": data.get("source_asset_type"),
                "source_asset_id": data.get("source_asset_id"),
                "config_json": json.dumps(data.get("config") or {}, sort_keys=True, ensure_ascii=False),
                "adapter_version": data.get("adapter_version") or "1.0",
            },
            user_id,
        )
    except Exception as exc:  # pragma: no cover - unexpected DB error surfaced as 400
        raise APIException(code=400, msg=f"创建适配器失败：{exc}", http_status=400) from exc


def list_adapters(
    db: Session, scenario_id: int, project_id: int
) -> list[ScenarioAdapter]:
    return repository.list_adapters(db, scenario_id, project_id)


def get_adapter(db: Session, adapter_id: int, project_id: int) -> ScenarioAdapter:
    row = repository.get_adapter(db, adapter_id, project_id)
    if not row:
        raise APIException(code=404, msg="适配器不存在", http_status=404)
    return row


def update_adapter(
    db: Session, adapter_id: int, project_id: int, data: dict[str, Any]
) -> ScenarioAdapter:
    row = get_adapter(db, adapter_id, project_id)
    target_status = data.get("status")
    if target_status is not None and target_status not in _VALID_STATUSES:
        raise APIException(code=400, msg=f"非法状态：{target_status}", http_status=400)
    return repository.update_adapter(
        db,
        row,
        {
            "status": target_status,
            "config_json": (
                json.dumps(data.get("config"), sort_keys=True, ensure_ascii=False)
                if data.get("config") is not None
                else None
            ),
            "adapter_version": data.get("adapter_version"),
        },
    )
