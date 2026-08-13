"""Requirement schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Document ──

class RequirementDocumentBrief(BaseModel):
    """需求文档列表项（轻量视图，不含全量 content 文本——P1-4 Schema 过宽修复）。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int = 0
    creator_id: int = 0
    creator_name: str = ""
    title: str = ""
    file_type: str = ""
    source_ref: str = ""
    source_url: str = ""
    status: str = "uploaded"
    imported_count: int = 0
    imported_func_count: int = 0
    imported_api_count: int = 0
    parsed_type: str = "requirement"
    extraction_status: str = "not_started"
    extraction_meta: str = "{}"
    doc_id: str = ""
    version: str = ""
    parent_id: Optional[int] = None
    diff_json: str = ""
    diff_status: str = "initial"
    created_at: Optional[datetime] = None


class RequirementDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int = 0
    creator_id: int = 0
    creator_name: str = ""
    title: str = ""
    file_type: str = ""
    source_ref: str = ""
    source_url: str = ""
    content: str = ""
    status: str = "uploaded"
    imported_count: int = 0
    imported_func_count: int = 0
    imported_api_count: int = 0
    parsed_type: str = "requirement"    # "requirement" | "test_cases"
    excel_cases: list[dict] = []        # direct Excel rows when parsed_type == "test_cases"
    extraction_status: str = "not_started"  # not_started | pending_review | confirmed
    # Version diff fields (batch-26)
    doc_id: str = ""
    version: str = ""
    parent_id: Optional[int] = None
    diff_json: str = ""
    diff_status: str = "initial"  # initial | update
    linked_swagger_id: Optional[int] = None
    linked_api_endpoint_ids: list[int] = Field(default_factory=list)
    created_at: Optional[datetime] = None


# ── AI Generated Case ──

class AIGeneratedCase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    index: int = 0
    title: str = ""
    case_type: str = "manual"       # manual
    priority: str = "P2"            # P0 / P1 / P2 / P3
    domain: str = ""
    module: str = ""
    case_design_method: str = ""      # 等价类划分 / 边界值分析 / 场景法 / 错误推测 / 组合覆盖
    positive_negative: str = ""       # positive / negative / boundary
    test_data_note: str = ""          # 用例输入数据的业务含义与来源说明
    preconditions: str = ""
    steps: str = "[]"               # JSON string
    expected_result: str = ""
    api_method: str = ""
    api_endpoint: str = ""
    api_headers: str = "{}"         # JSON: 请求头
    api_body: str = ""              # JSON: 请求参数（贴合真实业务）
    api_assertions: str = "[]"      # JSON: 断言数组
    remark: str = ""
    imported: bool = False          # whether this case has been imported
    client_scope: list[str] = []    # ["app", "pc", "web"] — applicable client platforms
    inherited: bool = Field(False, alias="_inherited")
    from_version: str = Field("", alias="_from_version")


# ── Requirement Analysis (two-phase AI output) ──

class Issue(BaseModel):
    severity: str = "info"          # "high" | "medium" | "low"
    description: str = ""
    suggestion: str = ""


class ExtractedRequirement(BaseModel):
    id: str = ""                    # "REQ-1"
    title: str = ""                 # Short label
    description: str = ""           # Detailed description
    type: str = "functional"        # "functional" | "ui" | "data" | "integration"
    issues: list[Issue] = []


class RequirementAnalysis(BaseModel):
    extracted_requirements: list[ExtractedRequirement] = []
    overall_assessment: str = ""


class AIGenerateResult(BaseModel):
    document_id: int
    requirement_analysis: RequirementAnalysis | None = None
    functional_cases: list[AIGeneratedCase] = []
    api_cases: list[AIGeneratedCase] = []
    raw_response: str = ""
    extraction_summary: str = ""  # Lanhu extraction status info


# ── Stage 1: Feature Extraction ──

class TestFunctionPoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = ""                    # "FP-1"
    title: str = ""                 # Short label
    description: str = ""           # Detailed description
    type: str = "functional"        # functional | ui | data | integration
    client_scope: list[str] = []    # ["app", "pc", "web"] — applicable client platforms
    issues: list[Issue] = []
    inherited: bool = Field(False, alias="_inherited")
    from_version: str = Field("", alias="_from_version")


class VersionInfo(BaseModel):
    """Parsed version information from changelog."""
    version: str = ""
    title: str = ""
    update_items: list[str] = []
    clients: list[str] = []
    folder_hint: str = ""


class TestModule(BaseModel):
    id: str = ""                    # "MOD-1"
    name: str = ""
    description: str = ""
    function_points: list[TestFunctionPoint] = []


class FeatureExtractionResult(BaseModel):
    document_id: int
    modules: list[TestModule] = []
    overall_assessment: str = ""
    raw_response: str = ""
    extraction_summary: str = ""
    extraction_status: str = "not_started"
    extraction_meta: str = "{}"
    version_info: list[VersionInfo] = []   # parsed version info from changelog
    client_summary: str = ""               # e.g. "本需求涉及 App端、PC端"
    # Version diff (batch-26)
    diff_summary: dict | None = None       # { new_pages, modified_pages, unchanged_pages, deleted_pages }
    inherited_from_version: str = ""       # e.g. "14.1.0" — which version unchanged FPs came from
    inherited_fp_count: int = 0            # number of function points inherited from parent


class ExtractionQualityOut(BaseModel):
    """batch-167: 提取完整度与降级状态（提取质量门禁的展示口径）。"""
    document_id: int
    mode: str = "single"            # single | chunked
    chunks: int = 1
    truncated: bool = False
    fallback: bool = False
    module_count: int = 0
    function_point_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    extraction_meta: str = "{}"


class ExtractionConfirmRequest(BaseModel):
    action: str = "confirm"          # confirm | reject
    modules: list[dict] = []         # confirmed/edited modules (for confirm action)
    rejected_modules: list[str] = [] # module IDs to re-extract (for reject action)
    rejected_notes: str = ""         # feedback for AI re-extraction


class GenerateRequest(BaseModel):
    use_extraction: bool = False


# ── Import ──

class CaseImportRequest(BaseModel):
    indices: list[int]
    edited_cases: list[AIGeneratedCase] = Field(default_factory=list)
    create_plan: bool = False


class CaseImportResult(BaseModel):
    imported: int
    skipped: int
    total: int
    plan_id: int | None = None
    plan_name: str = ""


class RequirementReviewRequest(BaseModel):
    action: Literal["approve", "reject", "edit"]
    edited_data: dict = Field(default_factory=dict)


class RequirementReviewCase(AIGeneratedCase):
    review_status: str = "pending"
    edited_data: dict | None = None


class RequirementReviewState(BaseModel):
    document_title: str = ""
    functional_cases: list[RequirementReviewCase] = Field(default_factory=list)
    api_cases: list[RequirementReviewCase] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


