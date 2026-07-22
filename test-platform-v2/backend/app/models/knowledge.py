"""知识中心模型 — 知识源 / 切片 / 图谱实体 / 图谱关系 / AI 产物 / Agent 执行记录。

对应《RAG 知识图谱与 Agent 持续学习能力落地执行文档》§6。
本期（M0+M1）仅接线 knowledge_source / knowledge_chunk / ai_artifact / agent_run；
knowledge_entity / knowledge_relation 建表留给 M3 知识图谱。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class KnowledgeSource(Base, TimestampMixin):
    """所有进入知识系统的原始资料（需求/接口/用例/缺陷/执行结果等）。"""
    __tablename__ = "knowledge_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    # requirement/openapi/test_case/defect/execution/code_diff/db_schema/manual
    source_type: Mapped[str] = mapped_column(default="manual", index=True)
    source_id: Mapped[int | None] = mapped_column(default=None, index=True)  # 关联业务表 ID，可为空
    title: Mapped[str] = mapped_column(default="")
    source_ref: Mapped[str] = mapped_column(default="")       # 文件名/URL/Swagger 地址/外链
    content_hash: Mapped[str] = mapped_column(default="", index=True)  # 去重与版本识别
    version: Mapped[str] = mapped_column(default="")
    iteration_id: Mapped[int | None] = mapped_column(default=None, index=True)
    # PARA 分类: inbox/project/area/resource/archive/wiki/skill
    para_category: Mapped[str] = mapped_column(default="inbox", index=True)
    # 知识域: project（项目知识）/ platform（平台研发知识）
    knowledge_domain: Mapped[str] = mapped_column(default="project", index=True)
    # 保鲜评分: 1.0=fresh, 0.0=stale
    freshness_score: Mapped[float] = mapped_column(default=1.0)
    last_verified_at: Mapped[datetime | None] = mapped_column(default=None)
    # pending/parsed/indexed/failed/deprecated
    status: Mapped[str] = mapped_column(default="pending", index=True)
    raw_content: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    # 知识溯源：模块名（从 source_ref 中自动提取，如 "Agent Team", "API层"）
    module_name: Mapped[str | None] = mapped_column(String(200), default=None)
    # FK to requirement_module (batch-27 M1) — nullable, not all sources are from a module
    module_id: Mapped[int | None] = mapped_column(
        default=None, index=True
    )


class KnowledgeChunk(Base):
    """知识切片 —— RAG 检索最小单位（本期仅入库，embedding 留 M2）。"""
    __tablename__ = "knowledge_chunk"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    source_id: Mapped[int] = mapped_column(index=True)  # -> knowledge_source.id
    # requirement_rule/api_schema/field_rule/defect_case/test_case/execution_result
    chunk_type: Mapped[str] = mapped_column(default="", index=True)
    title: Mapped[str] = mapped_column(default="")
    content: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(default="", index=True)
    token_count: Mapped[int] = mapped_column(default=0)
    embedding_id: Mapped[str] = mapped_column(default="")  # 外部/本地向量 ID，M2 填充
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组
    status: Mapped[str] = mapped_column(default="active", index=True)  # active/deprecated
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class KnowledgeVector(Base):
    """知识切片向量（M2）—— 与 chunk 1:1，dev 存 float32 BLOB，升 PG 切 pgvector。

    检索时 JOIN knowledge_chunk 取 status="active"（本表不冗余 chunk 状态）。
    """
    __tablename__ = "knowledge_vector"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[int] = mapped_column(index=True, unique=True)  # -> knowledge_chunk.id
    project_id: Mapped[int] = mapped_column(index=True)
    model: Mapped[str] = mapped_column(default="")   # 生成向量的嵌入模型（回填/切模型可辨识）
    dim: Mapped[int] = mapped_column(default=0)
    vec: Mapped[bytes] = mapped_column(LargeBinary)  # float32 小端字节，已 L2 归一化
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class KnowledgeEntity(Base, TimestampMixin):
    """知识图谱节点（M3 建图使用，本期仅建表）。"""
    __tablename__ = "knowledge_entity"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    # project/service/module/api/field/requirement/rule/test_case/defect/iteration
    entity_type: Mapped[str] = mapped_column(default="", index=True)
    # 稳定唯一键，如 api:camel-service:GET:/ee/test/matchpush
    entity_key: Mapped[str] = mapped_column(default="", index=True)
    name: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(Text, default="")
    source_id: Mapped[int | None] = mapped_column(default=None)
    business_ref_type: Mapped[str] = mapped_column(default="")
    business_ref_id: Mapped[int | None] = mapped_column(default=None)
    confidence: Mapped[float] = mapped_column(default=0.0)
    review_status: Mapped[str] = mapped_column(default="pending", index=True)  # pending/approved/rejected
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class KnowledgeRelation(Base):
    """知识图谱边（M3 建图使用，本期仅建表）。"""
    __tablename__ = "knowledge_relation"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    from_entity_id: Mapped[int] = mapped_column(index=True)
    # affects/contains/has_field/covers/exposes/depends_on/generated_from/executed_by
    relation_type: Mapped[str] = mapped_column(default="", index=True)
    to_entity_id: Mapped[int] = mapped_column(index=True)
    confidence: Mapped[float] = mapped_column(default=0.0)
    evidence_chunk_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组
    review_status: Mapped[str] = mapped_column(default="pending", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class AiArtifact(Base):
    """AI 生成草稿 —— 先进审核台，审核通过才导入正式资产。"""
    __tablename__ = "ai_artifact"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    # impact_analysis/test_case/test_data/business_rule/regression_scope
    artifact_type: Mapped[str] = mapped_column(default="", index=True)
    title: Mapped[str] = mapped_column(default="")
    content_json: Mapped[str] = mapped_column(Text, default="{}")  # 结构化生成内容
    source_refs: Mapped[str] = mapped_column(Text, default="[]")   # 引用的需求/接口/缺陷/用例
    agent_run_id: Mapped[int | None] = mapped_column(default=None, index=True)
    confidence: Mapped[float] = mapped_column(default=0.0)
    # pending/approved/rejected/imported
    review_status: Mapped[str] = mapped_column(default="pending", index=True)
    reviewer_id: Mapped[int] = mapped_column(default=0)
    review_comment: Mapped[str] = mapped_column(Text, default="")
    imported_ref_type: Mapped[str] = mapped_column(default="")  # 导入后的正式对象类型
    imported_ref_id: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class AgentRun(Base):
    """Agent 执行记录 —— 每次运行的输入/检索上下文/输出/状态可追踪。"""
    __tablename__ = "agent_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    # requirement/api_asset/impact/case_generation/test_data/execution/failure_analysis
    agent_type: Mapped[str] = mapped_column(default="", index=True)
    # manual/requirement_updated/swagger_updated/task_finished/schedule
    trigger_type: Mapped[str] = mapped_column(default="manual")
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    retrieved_context_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    # pending/running/success/failed/cancelled
    status: Mapped[str] = mapped_column(default="pending", index=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(default=0)
    operator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class AgentQueueItem(Base):
    """Agent 任务队列（M5）—— 持久化排队，支持并发控制和重试。"""
    __tablename__ = "agent_queue_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    # requirement_analysis/impact_analysis/case_generation/failure_analysis
    agent_type: Mapped[str] = mapped_column(default="", index=True)
    # manual/auto_trigger
    trigger_type: Mapped[str] = mapped_column(default="manual")
    # 0=auto, 10=manual（数值越大优先级越高）
    priority: Mapped[int] = mapped_column(default=0)
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    # pending/running/completed/failed/cancelled
    status: Mapped[str] = mapped_column(default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=1)
    error_message: Mapped[str] = mapped_column(Text, default="")
    operator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class KnowledgeIteration(Base, TimestampMixin):
    """迭代知识包（M6）—— 按迭代/版本归档知识快照。"""
    __tablename__ = "knowledge_iteration"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    iteration_name: Mapped[str] = mapped_column(default="")
    version: Mapped[str] = mapped_column(default="")
    start_date: Mapped[datetime | None] = mapped_column(default=None)
    end_date: Mapped[datetime | None] = mapped_column(default=None)
    # active/closed
    status: Mapped[str] = mapped_column(default="active", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class KnowledgeSnapshot(Base):
    """知识快照（M6）—— 迭代关闭时自动捕获的统计数据。"""
    __tablename__ = "knowledge_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    iteration_id: Mapped[int] = mapped_column(index=True)
    # entity/relation/chunk/stats
    snapshot_type: Mapped[str] = mapped_column(default="", index=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
