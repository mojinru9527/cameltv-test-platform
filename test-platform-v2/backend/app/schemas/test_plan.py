"""测试计划 Schema — 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


# ── TestPlan ──────────────────────────────────────────

class PlanCreate(BaseModel):
    plan_id: str = ""
    name: str
    description: str = ""
    status: str = "draft"            # draft / active / completed / archived
    assignee_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    auto_defect_on_fail: bool = False


class PlanUpdate(BaseModel):
    plan_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    auto_defect_on_fail: Optional[bool] = None


class PlanStats(BaseModel):
    total: int = 0
    pending: int = 0
    pass_: int = 0
    fail: int = 0
    skip: int = 0
    block: int = 0


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int = 0
    plan_id: str = ""
    name: str = ""
    description: str = ""
    status: str = "draft"
    creator_id: int = 0
    assignee_id: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assignee_name: str = ""
    auto_defect_on_fail: bool = False
    # Batch 149 (C147-4): 计划进度（前端列表直接展示），由 service 填充
    stats: PlanStats = PlanStats()


# ── PlanCase (计划内用例) ──────────────────────────────

class PlanCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    case_id: int
    sort_order: int = 0
    last_status: str = "pending"
    last_executed_at: Optional[datetime] = None
    executor_id: int = 0

    # 内联的用例摘要字段 (由 service 层填充)
    case_title: str = ""
    case_id_code: str = ""
    domain: str = ""
    module: str = ""
    priority: str = "P2"
    case_type: str = "manual"
    source_req_id: str = ""


class PlanCaseAdd(BaseModel):
    case_ids: list[int]           # 要添加的用例 ID 列表


class PlanCaseSort(BaseModel):
    sort_order: int


# ── Execution ─────────────────────────────────────────

class ExecutionCreate(BaseModel):
    status: Literal["pass", "fail", "skip", "block"]
    actual_result: str = ""
    notes: str = ""


class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_case_id: int
    executor_id: int = 0
    status: str = "pending"
    actual_result: str = ""
    notes: str = ""
    trace_id: str = ""
    kibana_link: str = ""
    executed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Batch 148 (C147-2): 失败根因独立字段（历史行由 service 从 actual_result 回填）
    status_code: int = 0
    error_type: str = ""
    error_message: str = ""

    # 内联
    case_id: int = 0
    case_title: str = ""
    executor_name: str = ""


# ── PlanDetail (含用例列表 + 统计) ─────────────────────

class PlanDetailOut(PlanOut):
    cases: list[PlanCaseOut] = []
    stats: PlanStats = PlanStats()


