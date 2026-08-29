"""WorkflowDataBuilder (V32-008): fixed business-action interface.

The workflow builder is an interface only — it does not depend on AI or a
browser. It declares a business action sequence a runner may execute.
"""
from __future__ import annotations

import json

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import DataSourceType
from app.modules.aitde.data.models import DataRequirement, DataSource
from app.modules.aitde.data.strategies.base import BaseBuilder, BuildResult, EntitySpec


class WorkflowDataBuilder(BaseBuilder):
    def build(
        self,
        source: DataSource | None,
        requirement: DataRequirement,
        environment_id: int | None,
        project_id: int,
    ) -> BuildResult:
        if source is not None and source.source_type != DataSourceType.WORKFLOW.value:
            raise APIException(code=400, msg="WORKFLOW 策略需要 WORKFLOW 数据源", http_status=400)
        if environment_id is None:
            raise APIException(code=400, msg="WORKFLOW 策略需要指定环境", http_status=400)

        # Fixed business action contract — no AI / browser dependency.
        actions = [
            {"entity": requirement.entity_type, "action": "create", "params": json.loads(requirement.constraints_json or "{}")}
        ]
        spec = EntitySpec(
            entity_type=requirement.entity_type,
            logical_key=requirement.requirement_key,
            physical_ref={"kind": "workflow", "environment_id": environment_id, "actions": actions},
            created_by_fixture=True,
            cleanup_action={"action": "revert", "actions": actions},
        )
        return BuildResult(entities=[spec], risk_note="workflow")
