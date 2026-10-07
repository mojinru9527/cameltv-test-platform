"""执行运行时服务（从 AITDE execution.service 抽离的最小集）。

保留 Run 生命周期的最小语义：创建时必须绑定「场景 + 场景版本 + 冻结契约版本 +
环境快照」；``runtime_status``（调度状态）与 ``outcome``（业务结论）分离。

删除 AITDE/Temporal 后，不再检查 Worker 在线、不再提交 Temporal Workflow：
执行由 runner 协议（campaign_execution 的 claim/heartbeat/report）完成。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.execution_runtime.enums import EvidenceStatus, RunStatus, TriggerType
from app.modules.execution_runtime import repository
from app.modules.execution_runtime.models import ExecutionRun
from app.modules.execution_runtime.scenario_models import TestScenario, TestScenarioVersion


def _validate_run_binding(
    db: Session,
    project_id: int,
    scenario_id: int,
    scenario_version_id: int,
    contract_version_id: int,
) -> None:
    """A run binds a project-owned scenario version and its frozen contract version."""
    scenario = db.scalar(
        select(TestScenario).where(
            TestScenario.id == scenario_id, TestScenario.project_id == project_id
        )
    )
    if not scenario:
        raise APIException(code=400, msg="场景不属于当前项目", http_status=400)

    version = db.scalar(
        select(TestScenarioVersion).where(
            TestScenarioVersion.id == scenario_version_id,
            TestScenarioVersion.scenario_id == scenario_id,
        )
    )
    if not version:
        raise APIException(code=400, msg="场景版本不存在或不匹配", http_status=400)
    if version.contract_version_id != contract_version_id:
        raise APIException(
            code=400, msg="场景版本与契约版本不匹配", http_status=400
        )


def create_run(
    db: Session,
    data: dict[str, Any],
    project_id: int,
    user_id: int,
) -> ExecutionRun:
    scenario_id = int(data.get("scenario_id") or 0)
    scenario_version_id = int(data.get("scenario_version_id") or 0)
    contract_version_id = int(data.get("contract_version_id") or 0)
    environment_snapshot_id = data.get("environment_snapshot_id")
    mission_id = int(data.get("mission_id") or 0)
    environment_id = int(data.get("environment_id") or 0)

    if not scenario_id or not scenario_version_id or not contract_version_id:
        raise APIException(
            code=400, msg="场景、场景版本与契约版本必须全部绑定", http_status=400
        )
    if not environment_snapshot_id:
        raise APIException(
            code=400, msg="Run 必须绑定环境快照（environment_snapshot_id）", http_status=400
        )

    _validate_run_binding(db, project_id, scenario_id, scenario_version_id, contract_version_id)

    trigger_type = data.get("trigger_type") or TriggerType.MANUAL.value
    row = repository.create_run(
        db,
        {
            "project_id": project_id,
            "mission_id": mission_id,
            "scenario_id": scenario_id,
            "scenario_version_id": scenario_version_id,
            "contract_version_id": contract_version_id,
            "adapter_id": data.get("adapter_id"),
            "environment_id": environment_id,
            "environment_snapshot_id": environment_snapshot_id,
            "runtime_status": RunStatus.QUEUED.value,
            "evidence_status": EvidenceStatus.PENDING.value,
            "trigger_type": trigger_type,
        },
        user_id,
    )
    return row


def get_run(db: Session, run_id: int, project_id: int) -> ExecutionRun:
    row = repository.get_run(db, run_id, project_id)
    if not row:
        raise APIException(code=404, msg="执行记录不存在", http_status=404)
    return row
