"""AITDE V3 shared enums (V30-001/V30-010).

Central enum definitions for the Mission aggregate's type/status/acceptance
vocabulary. String-valued so they map cleanly to ``String`` columns and remain
stable across DB backends.
"""
from __future__ import annotations

from enum import Enum


class MissionType(str, Enum):
    """Mission 类型（V3.0 先支持 VERSION，其余枚举保留）。"""

    VERSION = "VERSION"
    FEATURE = "FEATURE"
    HOTFIX = "HOTFIX"
    REGRESSION = "REGRESSION"
    EXPLORATORY = "EXPLORATORY"


class MissionStatus(str, Enum):
    """Mission 生命周期状态（V3.0 主链 DRAFT → ... → SCENARIO_READY → ARCHIVED）。"""

    DRAFT = "DRAFT"
    SOURCE_READY = "SOURCE_READY"
    SCOPE_ANALYZING = "SCOPE_ANALYZING"
    SCOPE_REVIEW = "SCOPE_REVIEW"
    CONTRACT_BUILDING = "CONTRACT_BUILDING"
    CONTRACT_REVIEW = "CONTRACT_REVIEW"
    CONTRACT_FROZEN = "CONTRACT_FROZEN"
    SCENARIO_BUILDING = "SCENARIO_BUILDING"
    SCENARIO_REVIEW = "SCENARIO_REVIEW"
    SCENARIO_READY = "SCENARIO_READY"
    ARCHIVED = "ARCHIVED"


class AcceptanceStatus(str, Enum):
    """验收状态（Gate 结果；绝对禁止 0 条执行 → PASS）。"""

    NOT_EVALUATED = "NOT_EVALUATED"
    NOT_READY = "NOT_READY"
    PASS = "PASS"
    FAIL = "FAIL"
