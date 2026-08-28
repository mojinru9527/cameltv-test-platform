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


class SourceType(str, Enum):
    """SourceArtifact 类型（V3.0 真正支持 REQUIREMENT/OPENAPI/MANUAL_NOTE）。"""

    REQUIREMENT = "REQUIREMENT"
    OPENAPI = "OPENAPI"
    WIKI = "WIKI"
    PROTOTYPE = "PROTOTYPE"
    HISTORICAL_CASE = "HISTORICAL_CASE"
    HISTORICAL_DEFECT = "HISTORICAL_DEFECT"
    MANUAL_NOTE = "MANUAL_NOTE"


class SourceRole(str, Enum):
    """Mission-Source 关联角色。"""

    REQUIREMENT = "REQUIREMENT"
    CONTRACT = "CONTRACT"
    SUPPORTING = "SUPPORTING"
    HISTORY = "HISTORY"


class ParseStatus(str, Enum):
    """Source 解析状态。"""

    PENDING = "PENDING"
    PARSING = "PARSING"
    PARSED = "PARSED"
    FAILED = "FAILED"


class ScopeType(str, Enum):
    FEATURE = "FEATURE"
    BUSINESS_FLOW = "BUSINESS_FLOW"
    PAGE = "PAGE"
    API = "API"
    DATA_STATE = "DATA_STATE"
    RISK = "RISK"
    REGRESSION_AREA = "REGRESSION_AREA"


class ScopeDecision(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


class TestDepth(str, Enum):
    FULL = "FULL"
    REGRESSION = "REGRESSION"
    SMOKE = "SMOKE"
    OBSERVE = "OBSERVE"


class RiskLevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ReviewStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ActorType(str, Enum):
    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"


class AmbiguityStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DEFERRED = "DEFERRED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
