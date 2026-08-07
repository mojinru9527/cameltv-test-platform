"""Schedule schemas with cron expression validation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, ConfigDict, field_validator


class ScheduleCreate(BaseModel):
    name: str
    description: str = ""
    plan_id: Optional[int] = None
    job_type: str = "plan"   # plan | ui（B112-3：UI job 定时）
    job_id: Optional[int] = None
    cron_expression: str
    enabled: bool = True

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, v: str) -> str:
        if v not in ("plan", "ui"):
            raise ValueError("job_type 仅支持 plan|ui")
        return v

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        try:
            CronTrigger.from_crontab(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"无效的 Cron 表达式: {e}") from e
        return v


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    plan_id: Optional[int] = None
    job_type: Optional[str] = None
    job_id: Optional[int] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            CronTrigger.from_crontab(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"无效的 Cron 表达式: {e}") from e
        return v


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    name: str = ""
    description: str = ""
    plan_id: Optional[int] = 0
    job_type: str = "plan"
    job_id: Optional[int] = None
    cron_expression: str = ""
    enabled: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    creator_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    plan_name: str = ""


class ScheduleRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    status: str = "running"
    result: Optional[dict] = None
    error_message: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
