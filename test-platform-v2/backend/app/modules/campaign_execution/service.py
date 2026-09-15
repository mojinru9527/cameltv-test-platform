from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.environment import Environment
from app.models.test_case import TestCase
from app.modules.aitde.execution import repository
from app.modules.aitde.execution import service as execution_service
from app.modules.aitde.execution.models import EnvironmentSnapshot, ExecutionRun, ScenarioAdapter
from app.modules.aitde.legacy_cutover.enums import LegacyObjectType
from app.modules.aitde.legacy_cutover.models import LegacyObjectMapping
from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion
from app.modules.campaign_execution.models import CampaignItem, TestCampaign

_API_SOURCE_ASSET_TYPES = ("TEST_CASE", "API_CASE", "api_case")


def start_campaign(db: Session, *, project_id: int, campaign_id: int, user_id: int) -> list[ExecutionRun]:
    campaign = db.scalar(
        select(TestCampaign).where(TestCampaign.id == campaign_id, TestCampaign.project_id == project_id)
    )
    if campaign is None:
        raise APIException(code=404, msg="测试活动不存在", http_status=404)
    items = db.scalars(
        select(CampaignItem)
        .where(CampaignItem.campaign_id == campaign_id, CampaignItem.enabled.is_(True))
        .order_by(CampaignItem.sequence)
    ).all()
    if not items:
        raise APIException(code=400, msg="测试活动没有可执行资产", http_status=400)
    runs: list[ExecutionRun] = []
    for item in items:
        try:
            cfg = json.loads(item.config_json or "{}")
            scenario_id = int(cfg["scenario_id"])
            scenario_version_id = int(cfg["scenario_version_id"])
            contract_version_id = int(cfg["contract_version_id"])
            environment_snapshot_id = int(cfg["environment_snapshot_id"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise APIException(
                code=400, msg=f"CampaignItem #{item.id} 缺少 canonical Run 绑定", http_status=400
            ) from exc
        run = execution_service.create_run(
            db,
            {
                "campaign_id": campaign.id,
                "campaign_item_id": item.id,
                "mission_id": int(cfg.get("mission_id") or 0),
                "scenario_id": scenario_id,
                "scenario_version_id": scenario_version_id,
                "contract_version_id": contract_version_id,
                "adapter_id": cfg.get("adapter_id"),
                "environment_id": campaign.environment_id,
                "environment_snapshot_id": environment_snapshot_id,
                "trigger_type": "CAMPAIGN",
            },
            project_id=project_id,
            user_id=user_id,
        )
        runs.append(run)
    campaign.status = "running"
    db.commit()
    return runs


def create_api_task_campaign(
    db: Session, *, project_id: int, user_id: int, name: str, cases: list[TestCase], environment_id: int | None
) -> tuple[TestCampaign, list[ExecutionRun]]:
    if environment_id is None:
        raise APIException(code=400, msg="canonical API 批量执行必须提供 environment_id", http_status=400)
    environment = db.scalar(
        select(Environment).where(Environment.id == environment_id, Environment.project_id == project_id)
    )
    if environment is None:
        raise APIException(code=404, msg="环境不存在或不属于当前项目", http_status=404)
    bindings = [(case, _resolve_api_case_binding(db, project_id, case.id)) for case in cases]
    snapshot_id = _ensure_environment_snapshot(db, environment.id)
    campaign = TestCampaign(
        project_id=project_id,
        name=f"{name} [{uuid.uuid4().hex[:8].upper()}]",
        type="api_batch",
        environment_id=environment.id,
        strategy_json=json.dumps({"source": "api_task"}, ensure_ascii=False),
        status="draft",
        created_by=user_id,
    )
    db.add(campaign)
    db.flush()
    for sequence, (case, binding) in enumerate(bindings, start=1):
        scenario_id, scenario_version_id, contract_version_id, mission_id, adapter_id = binding
        db.add(
            CampaignItem(
                campaign_id=campaign.id,
                asset_type="api_case",
                asset_id=case.id,
                sequence=sequence,
                config_json=json.dumps(
                    {
                        "mission_id": mission_id,
                        "scenario_id": scenario_id,
                        "scenario_version_id": scenario_version_id,
                        "contract_version_id": contract_version_id,
                        "environment_snapshot_id": snapshot_id,
                        "adapter_id": adapter_id,
                    },
                    ensure_ascii=False,
                ),
            )
        )
    db.commit()
    db.refresh(campaign)
    runs = start_campaign(db, project_id=project_id, campaign_id=campaign.id, user_id=user_id)
    return campaign, runs


def _resolve_api_case_binding(db: Session, project_id: int, case_id: int) -> tuple[int, int, int, int, int | None]:
    adapter = db.scalar(
        select(ScenarioAdapter)
        .join(TestScenario, ScenarioAdapter.scenario_id == TestScenario.id)
        .where(
            TestScenario.project_id == project_id,
            ScenarioAdapter.source_asset_id == case_id,
            ScenarioAdapter.source_asset_type.in_(_API_SOURCE_ASSET_TYPES),
        )
        .order_by(ScenarioAdapter.id.desc())
    )
    if adapter is not None:
        scenario = db.get(TestScenario, adapter.scenario_id)
        version = db.get(TestScenarioVersion, adapter.scenario_version_id)
        if (
            scenario is None
            or scenario.project_id != project_id
            or version is None
            or version.scenario_id != scenario.id
            or not version.contract_version_id
        ):
            raise APIException(code=409, msg=f"API 用例 {case_id} 的 canonical adapter 绑定无效", http_status=409)
        return scenario.id, version.id, version.contract_version_id, scenario.mission_id, adapter.id

    mapping = db.scalar(
        select(LegacyObjectMapping)
        .where(
            LegacyObjectMapping.project_id == project_id,
            LegacyObjectMapping.legacy_type == LegacyObjectType.TEST_CASE.value,
            LegacyObjectMapping.legacy_id == case_id,
            LegacyObjectMapping.canonical_type == "TEST_SCENARIO",
        )
        .order_by(LegacyObjectMapping.id.desc())
    )
    if mapping is not None:
        scenario = db.get(TestScenario, mapping.canonical_id)
        version = db.scalar(
            select(TestScenarioVersion)
            .where(TestScenarioVersion.scenario_id == mapping.canonical_id)
            .order_by(TestScenarioVersion.version_no.desc())
            .limit(1)
        )
        if scenario is None or scenario.project_id != project_id or version is None or not version.contract_version_id:
            raise APIException(code=409, msg=f"API 用例 {case_id} 的 canonical 映射无效", http_status=409)
        return scenario.id, version.id, version.contract_version_id, scenario.mission_id, None

    raise APIException(
        code=409, msg=f"API 用例 {case_id} 尚未迁移到 canonical Scenario，请先完成资产迁移", http_status=409
    )


def _ensure_environment_snapshot(db: Session, environment_id: int) -> int:
    snapshot = db.scalar(
        select(EnvironmentSnapshot)
        .where(EnvironmentSnapshot.environment_id == environment_id, EnvironmentSnapshot.mission_id == 0)
        .order_by(EnvironmentSnapshot.id.desc())
        .limit(1)
    )
    if snapshot is None:
        snapshot = repository.create_snapshot(
            db,
            {"manual_note": "auto-created by canonical API task adapter"},
            environment_id=environment_id,
            mission_id=0,
        )
    return snapshot.id
