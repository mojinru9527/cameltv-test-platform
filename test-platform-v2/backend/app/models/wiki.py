"""LLM-Wiki 知识库模型 —— Raw Source / Wiki 页面 / 链接 / 编译任务。

平台简化批次：差异对比（wiki_diff_task / wiki_diff_item）、lint、外部连接器
（external_wiki_connection）与审查相关表已删除；保留 Wiki 核心页表：
  - wiki_raw_source：蓝湖等原始来源（不可变、可 supersede），可绑 knowledge_source。
  - wiki_page / wiki_link：LLM 编译出的结构化 Wiki 页面与页面级链接。
  - wiki_ingest_job：两阶段编译任务（analysis→generation）状态。

设计沿用知识中心约定：project_id 松散作用域（无 FK）、枚举以 str + 注释、JSON 存 Text。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class WikiRawSource(Base, TimestampMixin):
    """原始来源（事实层）—— LLM 不可改写；内容变化则新建版本，旧版标 superseded。"""
    __tablename__ = "wiki_raw_source"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    # lanhu/requirement/openapi/test_case/defect/execution/manual
    source_type: Mapped[str] = mapped_column(default="lanhu", index=True)
    source_ref: Mapped[str] = mapped_column(default="")          # 蓝湖 URL / 文件名 / 外链
    # requirement_document/api_endpoint/test_case...
    business_ref_type: Mapped[str] = mapped_column(default="")
    business_ref_id: Mapped[int | None] = mapped_column(default=None, index=True)
    knowledge_source_id: Mapped[int | None] = mapped_column(default=None, index=True)  # -> knowledge_source.id
    title: Mapped[str] = mapped_column(default="")
    content_md: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(default="", index=True)      # SHA-256，去重与版本识别
    immutable_version: Mapped[str] = mapped_column(default="", index=True)  # docId+versionId+pageId 或文件 hash
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    # active/superseded/deprecated/failed
    status: Mapped[str] = mapped_column(default="active", index=True)


class WikiPage(Base, TimestampMixin):
    """Wiki 页面 —— LLM 编译生成的结构化 Markdown，带来源引用与审核状态。"""
    __tablename__ = "wiki_page"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    wiki_space_id: Mapped[int] = mapped_column(default=0, index=True)  # 预留多空间，默认 0
    # source/module/requirement/rule/api/entity/comparison/query/overview/index/log
    page_type: Mapped[str] = mapped_column(default="requirement", index=True)
    slug: Mapped[str] = mapped_column(default="", index=True)
    title: Mapped[str] = mapped_column(default="")
    content_md: Mapped[str] = mapped_column(Text, default="")
    frontmatter_json: Mapped[str] = mapped_column(Text, default="{}")
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]")   # raw_source_id / knowledge_source_id / lanhu page
    content_hash: Mapped[str] = mapped_column(default="", index=True)
    version: Mapped[int] = mapped_column(default=1)
    # draft/pending/approved/rejected/superseded
    review_status: Mapped[str] = mapped_column(default="pending", index=True)
    confidence: Mapped[float] = mapped_column(default=0.0)
    created_by_agent_run_id: Mapped[int | None] = mapped_column(default=None)


class WikiLink(Base):
    """Wiki 页面级链接 —— 与实体级 knowledge_relation 互补，可选双向同步。"""
    __tablename__ = "wiki_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    from_page_id: Mapped[int] = mapped_column(index=True)   # -> wiki_page.id
    to_page_id: Mapped[int] = mapped_column(index=True)     # -> wiki_page.id
    # mentions/depends_on/covers/affects/conflicts_with/source_of
    link_type: Mapped[str] = mapped_column(default="mentions", index=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    confidence: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class WikiIngestJob(Base):
    """Wiki 编译任务 —— 从 raw source 两阶段生成 Wiki（analysis→generation）。"""
    __tablename__ = "wiki_ingest_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    raw_source_id: Mapped[int] = mapped_column(index=True)  # -> wiki_raw_source.id
    # pending/running/success/failed/cancelled
    status: Mapped[str] = mapped_column(default="pending", index=True)
    # analysis/generation
    stage: Mapped[str] = mapped_column(default="analysis")
    analysis_json: Mapped[str] = mapped_column(Text, default="{}")  # 阶段 1 结构化产物
    result_json: Mapped[str] = mapped_column(Text, default="{}")    # 生成的页面/链接统计
    error_message: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(default=0)
    operator_id: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)



