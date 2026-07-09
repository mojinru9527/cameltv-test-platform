"""知识中心 Pydantic schemas —— 知识源 / 切片 / AI 产物 / Agent 执行记录 / 概览。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ── KnowledgeSource ──

class KnowledgeSourceOut(BaseModel):
    id: int
    project_id: int
    source_type: str
    source_id: int | None = None
    title: str
    source_ref: str
    content_hash: str
    version: str
    iteration_id: int | None = None
    status: str
    raw_content: str = ""
    metadata_json: str = "{}"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class KnowledgeSourceBrief(BaseModel):
    """列表用精简视图（不含 raw_content，避免大字段）。"""
    id: int
    project_id: int
    source_type: str
    source_id: int | None = None
    title: str
    source_ref: str
    version: str
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── KnowledgeChunk ──

class KnowledgeChunkOut(BaseModel):
    id: int
    project_id: int
    source_id: int
    chunk_type: str
    title: str
    content: str
    content_hash: str
    token_count: int
    embedding_id: str
    tags: str
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── AiArtifact ──

class AiArtifactOut(BaseModel):
    id: int
    project_id: int
    artifact_type: str
    title: str
    content_json: str
    source_refs: str
    agent_run_id: int | None = None
    confidence: float
    review_status: str
    reviewer_id: int
    review_comment: str
    imported_ref_type: str
    imported_ref_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ArtifactReviewRequest(BaseModel):
    comment: str = ""


class ArtifactImportRequest(BaseModel):
    """将审核通过的 AI 用例产物导入正式用例库。"""
    comment: str = ""


# ── AgentRun ──

class AgentRunOut(BaseModel):
    id: int
    project_id: int
    agent_type: str
    trigger_type: str
    input_json: str
    retrieved_context_json: str
    output_json: str
    status: str
    error_message: str
    duration_ms: int
    operator_id: int
    created_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── 概览 ──

class KnowledgeHealth(BaseModel):
    unreviewed_artifacts: int = 0      # 未审核 AI 产物
    deprecated_sources: int = 0        # 已废弃知识源
    sourceless_chunks: int = 0         # 无来源切片（孤儿）
    low_confidence_relations: int = 0  # 低置信度关系（M3 起用）


class KnowledgeOverviewOut(BaseModel):
    source_count: int = 0
    chunk_count: int = 0
    entity_count: int = 0
    pending_artifact_count: int = 0
    recent_sources: list[KnowledgeSourceBrief] = Field(default_factory=list)
    health: KnowledgeHealth = Field(default_factory=KnowledgeHealth)
