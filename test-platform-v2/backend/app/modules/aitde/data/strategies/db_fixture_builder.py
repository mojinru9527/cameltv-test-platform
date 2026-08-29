"""DbFixtureBuilder (V32-007): controlled INSERT/UPDATE within an allowlist.

Policy: source must be READWRITE on a non-production environment; tables must be
in the config allowlist; bounded row limit; idempotent compensation recorded.
"""
from __future__ import annotations

import json

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import DataSourceAccessMode, DataSourceType
from app.modules.aitde.data.models import DataRequirement, DataSource
from app.modules.aitde.data.strategies.base import BaseBuilder, BuildResult, EntitySpec

_ROW_LIMIT = 500


class DbFixtureBuilder(BaseBuilder):
    def build(
        self,
        source: DataSource | None,
        requirement: DataRequirement,
        environment_id: int | None,
        project_id: int,
    ) -> BuildResult:
        if source is None:
            raise APIException(code=400, msg="DB_FIXTURE 策略需要一个数据库数据源", http_status=400)
        if source.source_type not in (DataSourceType.MYSQL.value, DataSourceType.POSTGRES.value):
            raise APIException(code=400, msg="DB_FIXTURE 仅支持 MYSQL/POSTGRES 数据源", http_status=400)
        if source.access_mode != DataSourceAccessMode.READWRITE.value:
            raise APIException(code=400, msg="DB_FIXTURE 策略需要 READWRITE 数据源", http_status=400)

        config = json.loads(source.config_json or "{}")
        allowlist = set(str(t).lower() for t in config.get("table_allowlist", []))
        if not allowlist:
            raise APIException(code=400, msg="DB_FIXTURE 要求数据源配置 table_allowlist", http_status=400)
        if requirement.entity_type.lower() not in allowlist:
            raise APIException(
                code=400,
                msg=f"表 {requirement.entity_type} 不在 allowlist 中",
                http_status=400,
            )

        constraints = json.loads(requirement.constraints_json or "{}")
        spec = EntitySpec(
            entity_type=requirement.entity_type,
            logical_key=requirement.requirement_key,
            physical_ref={
                "kind": "write",
                "source_id": source.id,
                "environment_id": environment_id,
                "table": requirement.entity_type,
                "set": constraints,
                "row_limit": _ROW_LIMIT,
            },
            created_by_fixture=True,
            cleanup_action={"action": "delete", "table": requirement.entity_type, "where": constraints},
        )
        return BuildResult(entities=[spec], risk_note="db_write_allowlisted")
