from __future__ import annotations
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.exceptions import APIException
from app.modules.aitde.execution import service as execution_service
from app.modules.aitde.execution.models import ExecutionRun
from app.modules.campaign_execution.models import TestCampaign, CampaignItem


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
    runs = []
    for item in items:
        cfg = json.loads(item.config_json or "{}")
        run = execution_service.create_run(
            db,
            {
                "mission_id": 0,
                "scenario_id": int(cfg["scenario_id"]),
                "scenario_version_id": int(cfg["scenario_version_id"]),
                "contract_version_id": int(cfg["contract_version_id"]),
                "adapter_id": cfg.get("adapter_id"),
                "environment_id": campaign.environment_id,
                "environment_snapshot_id": int(cfg["environment_snapshot_id"]),
                "trigger_type": "CAMPAIGN",
            },
            project_id=project_id,
            user_id=user_id,
        )
        runs.append(run)
    campaign.status = "running"
    db.commit()
    return runs
