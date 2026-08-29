"""ApiDataBuilder (V32-006): create data through a test-environment API.

Produces a create spec (endpoint + payload) with a compensation (delete).
Policy: non-production environment only; source must be API type.
"""
from __future__ import annotations

import json

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import DataSourceType
from app.modules.aitde.data.models import DataRequirement, DataSource
from app.modules.aitde.data.strategies.base import BaseBuilder, BuildResult, EntitySpec


class ApiDataBuilder(BaseBuilder):
    def build(
        self,
        source: DataSource | None,
        requirement: DataRequirement,
        environment_id: int | None,
        project_id: int,
    ) -> BuildResult:
        if source is None:
            raise APIException(code=400, msg="API_BUILDER 策略需要一个 API 数据源", http_status=400)
        if source.source_type != DataSourceType.API.value:
            raise APIException(code=400, msg="API_BUILDER 仅支持 API 数据源", http_status=400)
        if environment_id is None:
            raise APIException(code=400, msg="API_BUILDER 需要指定环境", http_status=400)

        config = json.loads(source.config_json or "{}")
        endpoint = config.get("create_endpoint")
        if not endpoint:
            raise APIException(code=400, msg="API 数据源需配置 create_endpoint", http_status=400)

        constraints = json.loads(requirement.constraints_json or "{}")
        spec = EntitySpec(
            entity_type=requirement.entity_type,
            logical_key=requirement.requirement_key,
            physical_ref={
                "kind": "api_create",
                "source_id": source.id,
                "environment_id": environment_id,
                "endpoint": endpoint,
                "payload": constraints,
            },
            created_by_fixture=True,
            cleanup_action={"action": "api_delete", "endpoint": config.get("delete_endpoint", ""), "entity": requirement.entity_type},
        )
        return BuildResult(entities=[spec], risk_note="api_create")
