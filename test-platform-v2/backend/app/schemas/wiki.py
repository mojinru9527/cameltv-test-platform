"""LLM-Wiki 知识库 Schema —— 请求/响应 DTO（VNext-1..3）。

响应 DTO 加 model_config = {"from_attributes": True}；JSON 字段以 str 承载（对齐 Text-JSON 模型）。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════
# 配置 / 开关
# ══════════════════════════════════════════════

class WikiConfigOut(BaseModel):
    """前端据此决定 Wiki / 差异对比 Tab 与按钮可用性。"""
    wiki_enabled: bool = False
    wiki_auto_ingest_enabled: bool = False
    wiki_diff_enabled: bool = False
    wiki_auto_create_artifact: bool = False
    lanhu_mcp_enabled: bool = True


# ══════════════════════════════════════════════
# Raw Source（VNext-1）
# ══════════════════════════════════════════════

class WikiRawSourceBrief(BaseModel):
    id: int
    project_id: int
    source_type: str
    source_ref: str = ""
    title: str = ""
    content_hash: str = ""
    immutable_version: str = ""
    status: str = "active"
    knowledge_source_id: int | None = None
    doc_id: str = ""
    version_id: str = ""
    page_id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class WikiRawSourceOut(WikiRawSourceBrief):
    business_ref_type: str = ""
    business_ref_id: int | None = None
    content_md: str = ""
    metadata_json: str = "{}"


class LanhuImportTarget(BaseModel):
    ingest_knowledge: bool = True   # 是否同步进现有 RAG 知识库
    build_wiki: bool = True         # 是否触发 Wiki 编译（VNext-2）
    extract_graph: bool = True      # 是否抽取知识图谱


class LanhuImportRequest(BaseModel):
    url: str = Field(..., min_length=1, description="蓝湖设计稿页面链接")
    description: str = Field("", description="补充说明（图片型原型必填）")
    target: LanhuImportTarget = Field(default_factory=LanhuImportTarget)


class LanhuImportResult(BaseModel):
    raw_source_id: int | None = None
    knowledge_source_id: int | None = None
    wiki_job_id: int | None = None
    extraction_status: str  # success/partial/image_only/auth_failed/permission_denied/invalid_url/failed
    extraction_summary: str = ""


# ══════════════════════════════════════════════
# Wiki 编译任务 / 页面 / 链接（VNext-2）
# ══════════════════════════════════════════════

class WikiIngestJobOut(BaseModel):
    id: int
    project_id: int
    raw_source_id: int
    status: str
    stage: str
    result_json: str = "{}"
    error_message: str = ""
    retry_count: int = 0
    created_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class WikiIngestJobCreate(BaseModel):
    raw_source_id: int


class WikiPageBrief(BaseModel):
    id: int
    project_id: int
    page_type: str
    slug: str
    title: str
    version: int = 1
    review_status: str = "pending"
    confidence: float = 0.0
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class WikiPageOut(WikiPageBrief):
    content_md: str = ""
    frontmatter_json: str = "{}"
    source_refs_json: str = "[]"
    content_hash: str = ""
    created_by_agent_run_id: int | None = None
    created_at: datetime | None = None


class WikiLinkOut(BaseModel):
    id: int
    project_id: int
    from_page_id: int
    to_page_id: int
    link_type: str
    evidence_json: str = "{}"
    confidence: float = 0.0

    model_config = {"from_attributes": True}


class WikiReviewRequest(BaseModel):
    comment: str = ""


# ══════════════════════════════════════════════
# 知识库差异对比（VNext-3）
# ══════════════════════════════════════════════

class WikiDiffCreateRequest(BaseModel):
    title: str = Field("", max_length=200)
    compare_type: str = "rag_vs_wiki"      # rag_vs_wiki/wiki_vs_wiki/lanhu_version/external_llm_wiki
    query: str = Field(..., min_length=1)  # 需求名/关键词，用于在两侧知识库定位同一需求
    left_kb_type: str = "platform_rag"     # platform_rag/platform_wiki
    right_kb_type: str = "platform_wiki"


class WikiDiffItemOut(BaseModel):
    id: int
    task_id: int
    project_id: int
    dimension: str
    diff_type: str
    severity: str
    title: str
    left_value: str = ""
    right_value: str = ""
    evidence_json: str = "[]"
    suggestion: str = ""
    review_status: str = "pending"
    resolved_artifact_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class WikiDiffTaskBrief(BaseModel):
    id: int
    project_id: int
    title: str
    compare_type: str
    status: str
    summary_json: str = "{}"
    created_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class WikiDiffTaskOut(WikiDiffTaskBrief):
    left_ref_json: str = "{}"
    right_ref_json: str = "{}"
    error_message: str = ""
    items: list[WikiDiffItemOut] = Field(default_factory=list)


class WikiDiffItemReviewRequest(BaseModel):
    comment: str = ""


class WikiDiffCreateArtifactRequest(BaseModel):
    artifact_type: str = ""   # 留空则按维度自动映射


class WikiDiffCreateArtifactResult(BaseModel):
    artifact_id: int
    artifact_type: str


# ══════════════════════════════════════════════
# 外部 LLM-Wiki 连接器（VNext-5）
# ══════════════════════════════════════════════

class ExternalWikiConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    provider: str = Field(default="llm_wiki_desktop", max_length=50)
    base_url: str = Field(..., min_length=1, max_length=500)
    token: str = Field(default="", description="明文 token，服务端加密后存储")
    external_project_id: str | None = None
    enabled: bool = True


class ExternalWikiConnectionUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    base_url: str | None = None
    token: str | None = Field(default=None, description="留空则不更新 token")
    external_project_id: str | None = None
    enabled: bool | None = None


class ExternalWikiConnectionOut(BaseModel):
    id: int
    project_id: int
    name: str
    provider: str
    base_url: str
    # token_encrypted: 永不通过 API 暴露
    external_project_id: str | None = None
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExternalWikiSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)


class ExternalWikiPageRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=500)


class ExternalWikiGraphRequest(BaseModel):
    node: str = Field(..., min_length=1, max_length=500)


class ExternalWikiHealthResult(BaseModel):
    ok: bool
    version: str = ""
    message: str = ""


class ExternalWikiSearchResult(BaseModel):
    items: list[dict] = Field(default_factory=list)
    total: int = 0


class ExternalWikiPageResult(BaseModel):
    ok: bool
    title: str = ""
    content_md: str = ""
    meta: dict = Field(default_factory=dict)
    error: str = ""


class ExternalWikiGraphResult(BaseModel):
    ok: bool
    node: str = ""
    edges: list[dict] = Field(default_factory=list)
    nodes: list[dict] = Field(default_factory=list)
    error: str = ""


# ══════════════════════════════════════════════
# Wiki 健康体检 / Lint（VNext-6）
# ══════════════════════════════════════════════

class WikiLintRunRequest(BaseModel):
    """触发 lint 扫描。"""
    project_id_override: int | None = Field(default=None, description="管理员可覆盖项目范围")


class WikiLintReportBrief(BaseModel):
    id: int
    project_id: int
    status: str
    summary_json: str = "{}"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class WikiLintIssueOut(BaseModel):
    id: int
    report_id: int
    project_id: int
    rule: str
    severity: str = "P2"
    title: str
    description: str = ""
    entity_type: str = ""
    entity_id: int | None = None
    related_entity_json: str = "{}"
    suggestion: str = ""
    review_status: str = "pending"
    resolved_artifact_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class WikiLintReportOut(WikiLintReportBrief):
    error_message: str = ""
    issues: list[WikiLintIssueOut] = Field(default_factory=list)


class WikiLintConvertRequest(BaseModel):
    issue_ids: list[int] = Field(default_factory=list, description="要转换的问题 id 列表，空=全部")
    artifact_type: str = Field(default="", description="产物类型，留空按规则自动映射")
