"""AITDE V3.5 Legacy Schedule / TestPlan adapters (V35-009 / V35-010).

Map the legacy ``TestSchedule`` → ``Trigger`` and ``TestPlan`` → ``ExecutionCampaign``
/ ``RunProfile`` WITHOUT modifying the legacy records. V3.5 keeps the old write
paths; the official cutover is V4.0. These adapters let the Continuous Acceptance
read existing schedules/plans and re-run them as triggers/campaigns.

"旧 schedule 不破坏" (V35-009) and "旧 plan 可读" (V35-010) are satisfied because
the adapters only read + produce a new trigger/campaign; they never mutate legacy
rows.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import CampaignType, TriggerType
from app.modules.aitde.continuous import repository


class LegacyScheduleAdapter:
    """Map a legacy TestSchedule into a Trigger (read-only on the legacy row)."""

    def to_trigger(self, db: Session, schedule: Any, project_id: int) -> dict[str, Any]:
        config: dict[str, Any] = {
            "legacy_schedule_id": schedule.id,
            "cron": schedule.cron_expression or "",
            "job_type": schedule.job_type or "plan",
            "job_id": schedule.job_id,
            "plan_id": schedule.plan_id,
            "environment_id": schedule.environment_id,
        }
        # Find an existing trigger for this legacy schedule (idempotent).
        for t in repository.list_triggers(db, project_id):
            cfg = _parse_json(t.config_json)
            if cfg.get("legacy_schedule_id") == schedule.id:
                return _trigger_to_dict(t)
        row = repository.create_trigger(
            db,
            {
                "project_id": project_id,
                "mission_id": None,
                "trigger_type": TriggerType.SCHEDULE.value,
                "config_json": json.dumps(config),
                "status": "ACTIVE" if schedule.enabled else "DISABLED",
            },
        )
        return _trigger_to_dict(row)


class LegacyTestPlanAdapter:
    """Map a legacy TestPlan into an ExecutionCampaign (one snapshot per plan)."""

    def to_campaign(self, db: Session, plan: Any, project_id: int) -> dict[str, Any]:
        row = repository.create_campaign(
            db,
            {
                "project_id": project_id,
                "mission_id": plan.id,
                "name": f"plan-{plan.id}-{plan.name or 'plan'}",
                "campaign_type": CampaignType.CUSTOM.value,
                "environment_id": 0,
                "build_observation_id": None,
                "status": "DRAFT",
                "created_by_type": "LEGACY",
            },
        )
        return _campaign_to_dict(row)


def _parse_json(raw: str) -> dict[str, Any]:
    import json as _json

    try:
        v = _json.loads(raw or "{}")
        return v if isinstance(v, dict) else {}
    except (ValueError, TypeError):
        return {}


def _trigger_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "trigger_type": row.trigger_type,
        "config_json": row.config_json,
        "status": row.status,
        "last_fired_at": row.last_fired_at,
        "created_at": row.created_at,
    }


def _campaign_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "mission_id": row.mission_id,
        "name": row.name,
        "campaign_type": row.campaign_type,
        "environment_id": row.environment_id,
        "build_observation_id": row.build_observation_id,
        "status": row.status,
        "created_by_type": row.created_by_type,
        "created_at": row.created_at,
    }


schedule_adapter = LegacyScheduleAdapter()
test_plan_adapter = LegacyTestPlanAdapter()
