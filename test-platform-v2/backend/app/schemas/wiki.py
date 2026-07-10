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
