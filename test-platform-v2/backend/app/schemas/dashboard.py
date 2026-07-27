"""Dashboard schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CaseTypeStat(BaseModel):
    """单个用例类型的统计（带颜色标识）。"""
    case_type: str = ""             # manual / api / ui
    label: str = ""                 # 功能用例 / 接口用例 / 自动化用例
    color: str = ""                 # #1890ff / #52c41a / #fa8c16
    count: int = 0                  # 用例总数
    execution_total: int = 0        # 执行总次数
    execution_pass: int = 0         # 执行通过次数
    execution_fail: int = 0         # 执行失败次数
    pass_rate: float = 0.0          # 通过率 %
    fail_rate: float = 0.0          # 失败率 %


class CaseTypePriority(BaseModel):
    """单个用例类型按 P0-P3 优先级分布。"""
    case_type: str = ""             # manual / api / ui
    label: str = ""                 # 功能用例 / 接口用例 / 自动化用例
    color: str = ""                 # #1890ff / #52c41a / #fa8c16
    p0: int = 0
    p1: int = 0
    p2: int = 0
    p3: int = 0
    total: int = 0


class DashboardStats(BaseModel):
    """工作台聚合统计。"""
    total_cases: int = 0
    total_plans: int = 0
    api_cases: int = 0
    pass_rate: float = 0.0
    case_type_stats: list[CaseTypeStat] = []       # 按用例类型分组的执行统计
    priority_distribution: list[CaseTypePriority] = []  # 按用例类型 + 优先级分布
    time_range: Optional[dict] = None


# ── V2.5: Cross-project dashboard ──

class CrossProjectCard(BaseModel):
    """单个项目的指标卡片。"""
    project_id: int = 0
    project_name: str = ""
    total_cases: int = 0
    total_plans: int = 0
    api_cases: int = 0
    pass_rate: float = 0.0
    defect_count: int = 0


class CrossProjectAggregate(BaseModel):
    """全部项目的聚合汇总。"""
    total_projects: int = 0
    total_cases: int = 0
    total_plans: int = 0
    total_api_cases: int = 0
    overall_pass_rate: float = 0.0
    total_defects: int = 0


class TrendPoint(BaseModel):
    """跨项目趋势数据点。"""
    date: str = ""
    pass_rate: float | None = None
    total_execs: int | None = None
    count: int | None = None


class CrossProjectTrends(BaseModel):
    pass_rate: list[TrendPoint] = []
    defects: list[TrendPoint] = []


class CrossProjectStats(BaseModel):
    projects: list = []               # simplified project info [{id, code, name}]
    aggregate: CrossProjectAggregate = CrossProjectAggregate()
    per_project: list[CrossProjectCard] = []
    trends: CrossProjectTrends = CrossProjectTrends()
