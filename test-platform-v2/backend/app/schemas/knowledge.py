"""知识中心 Pydantic schemas —— 知识源 / 切片 / 图谱实体 / 图谱关系 / AI 产物 / Agent 执行记录 / 概览。"""
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
    para_category: str | None = None
    knowledge_domain: str | None = None
    freshness_score: float | None = None
    last_verified_at: datetime | None = None
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
    para_category: str | None = None
    knowledge_domain: str | None = None
    freshness_score: float | None = None
    last_verified_at: datetime | None = None
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
    low_confidence_relations: int = 0  # 低置信度关系（confidence < 0.5）
    unreviewed_relations: int = 0      # 待审核关系（M3 起用）
    # M4 Agent 指标
    agent_approval_rate: float = 0.0   # AI 产物采纳率
    agent_avg_duration_ms: int = 0     # Agent 平均耗时 (ms)
    agent_total_runs: int = 0          # Agent 执行总量


class KnowledgeOverviewOut(BaseModel):
    source_count: int = 0
    chunk_count: int = 0
    entity_count: int = 0
    pending_artifact_count: int = 0
    recent_sources: list[KnowledgeSourceBrief] = Field(default_factory=list)
    health: KnowledgeHealth = Field(default_factory=KnowledgeHealth)
    # M2 RAG 健康指标
    rag_enabled: bool = False
    embedding_model: str = ""
    active_chunks: int = 0
    embedded_chunks: int = 0
    embedding_coverage: float | None = None  # None 表示 RAG 未启用


class SearchHealthOut(BaseModel):
    """搜索健康检查响应。"""
    rag_enabled: bool = False
    embedding_model: str = ""
    embedding_available: bool = False
    vector_search_functional: bool = False
    fallback_mode: str = "keyword-only"  # "keyword-only" | "hybrid"
    active_chunks: int = 0
    embedded_chunks: int = 0
    embedding_coverage: float | None = None


# ── M2 混合检索 ──

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    chunk_type: str | None = None
    top_k: int = Field(8, ge=1, le=50)
    mode: str = "hybrid"  # hybrid | keyword | vector


class SearchResultOut(BaseModel):
    chunk_id: int
    chunk_type: str
    title: str
    snippet: str
    score: float
    source_id: int
    source_name: str


class ReembedResult(BaseModel):
    total: int = 0        # 本次扫描到的待嵌入 active 切片数
    embedded: int = 0     # 成功写入向量数
    skipped: int = 0      # 跳过数（无内容/嵌入失败）


# ── M3 知识图谱 ──

class KnowledgeEntityOut(BaseModel):
    id: int
    project_id: int
    entity_type: str
    entity_key: str
    name: str
    description: str
    source_id: int | None = None
    business_ref_type: str
    business_ref_id: int | None = None
    confidence: float
    review_status: str
    metadata_json: str = "{}"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class KnowledgeEntityBrief(BaseModel):
    """图谱节点——精简视图。"""
    id: int
    entity_type: str
    entity_key: str
    name: str
    description: str
    confidence: float

    model_config = {"from_attributes": True}


class KnowledgeRelationOut(BaseModel):
    id: int
    project_id: int
    from_entity_id: int
    relation_type: str
    to_entity_id: int
    confidence: float
    evidence_chunk_ids: str = "[]"
    review_status: str
    metadata_json: str = "{}"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class GraphNode(BaseModel):
    """可视化节点。"""
    id: str  # entity_type:entity_key
    entity_type: str
    name: str
    group: str = ""  # 按 entity_type 着色分组
    description: str = ""
    confidence: float = 0.0
    entity_id: int = 0  # DB PK for click-to-detail


class GraphEdge(BaseModel):
    """可视化边。"""
    source: str  # from node id
    target: str  # to node id
    relation_type: str
    confidence: float


class GraphViewOut(BaseModel):
    """力导向图数据。"""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class EntityExtractRequest(BaseModel):
    """触发实体提取请求。"""
    source_id: int | None = None  # 指定知识源（None=全项目扫描）
    max_chunks: int = Field(100, ge=1, le=500)


class EntityExtractResult(BaseModel):
    extracted: int = 0   # 新提取实体数
    relations: int = 0   # 新关系数
    skipped: int = 0     # 已存在跳过数
    message: str = ""


class RelationApprovalRequest(BaseModel):
    comment: str = ""


# ── M5 Agent 任务队列 ──

class AgentQueueItemOut(BaseModel):
    id: int
    project_id: int
    agent_type: str
    trigger_type: str
    priority: int
    input_json: str
    status: str
    retry_count: int
    max_retries: int
    error_message: str
    operator_id: int
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class QueueStats(BaseModel):
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0


# ── M6 迭代知识包 ──

class KnowledgeIterationOut(BaseModel):
    id: int
    project_id: int
    iteration_name: str
    version: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str
    description: str
    metadata_json: str = "{}"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class KnowledgeIterationCreate(BaseModel):
    iteration_name: str = Field(..., min_length=1, max_length=200)
    version: str = ""
    start_date: str | None = None  # ISO date
    end_date: str | None = None
    description: str = ""


class KnowledgeSnapshotOut(BaseModel):
    id: int
    iteration_id: int
    snapshot_type: str
    data_json: str = "{}"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CompareSnapshotsOut(BaseModel):
    base_iteration_id: int
    base_iteration_name: str = ""
    target_iteration_id: int
    target_iteration_name: str = ""
    deltas: dict = Field(default_factory=dict)
    trends: dict = Field(default_factory=dict)


# ── M6 回归预测 ──

class RegressionPredictionRequest(BaseModel):
    changed_paths: list[str] = Field(default_factory=list, description="变更的 API paths")
    changed_modules: list[str] = Field(default_factory=list, description="变更的模块名")


class RegressionPredictionItem(BaseModel):
    api_path: str = ""
    module: str = ""
    risk_score: float = 0.0  # 0-1
    historical_defects: int = 0
    suggested_test_cases: list[str] = Field(default_factory=list)
    affected_entities: list[str] = Field(default_factory=list)


class RegressionPredictionOut(BaseModel):
    items: list[RegressionPredictionItem] = Field(default_factory=list)
    total_analyzed: int = 0
    high_risk_count: int = 0
