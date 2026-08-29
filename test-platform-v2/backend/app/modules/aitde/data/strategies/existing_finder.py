"""ExistingDataFinder (V32-005): locate existing test data, never mutate.

Returns a read recipe (entity + constraints + row limit). Policy: the source
must be READONLY; constraint validation failure means no lease.
"""
from __future__ import annotations

import json

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import DataSourceAccessMode, DataSourceType
from app.modules.aitde.data.models import DataRequirement, DataSource
from app.modules.aitde.data.strategies.base import BaseBuilder, BuildResult, EntitySpec

_ROW_LIMIT = 100


class ExistingDataFinder(BaseBuilder):
    def build(
        self,
        source: DataSource | None,
        requirement: DataRequirement,
        environment_id: int | None,
        project_id: int,
    ) -> BuildResult:
        if source is None:
            raise APIException(code=400, msg="EXISTING 策略需要一个只读数据源", http_status=400)
        if source.access_mode != DataSourceAccessMode.READONLY.value:
            raise APIException(code=400, msg="EXISTING 策略仅支持只读数据源", http_status=400)
        if source.source_type not in (DataSourceType.MYSQL.value, DataSourceType.POSTGRES.value, DataSourceType.API.value):
            raise APIException(code=400, msg="EXISTING 策略不支持该数据源类型", http_status=400)

        constraints = json.loads(requirement.constraints_json or "{}")
        if not isinstance(constraints, dict) or not constraints:
            raise APIException(code=400, msg="约束为空，无法构建查找配方", http_status=400)

        spec = EntitySpec(
            entity_type=requirement.entity_type,
            logical_key=requirement.requirement_key,
            physical_ref={
                "kind": "read",
                "source_id": source.id,
                "environment_id": environment_id,
                "where": constraints,
                "row_limit": _ROW_LIMIT,
            },
            created_by_fixture=False,
            cleanup_action=None,
        )
        return BuildResult(entities=[spec], risk_note="existing_readonly")
