"""LLM-Wiki 知识库模型 —— Raw Source / Wiki 页面 / 链接 / 编译任务 / 差异任务 / 差异项。

对应《LLM-Wiki 知识库差异对比能力落地方案》§6。落地 VNext-1..3：
  - wiki_raw_source：蓝湖等原始来源（不可变、可 supersede），可绑 knowledge_source。
  - wiki_page / wiki_link：LLM 编译出的结构化 Wiki 页面与页面级链接。
  - wiki_ingest_job：两阶段编译任务（analysis→generation）状态。
  - wiki_diff_task / wiki_diff_item：同一需求在两知识库之间的差异任务与差异项。

设计沿用知识中心约定：project_id 松散作用域（无 FK）、枚举以 str + 注释、JSON 存 Text。
外部 LLM-Wiki 连接（wiki_external_connection）留待 VNext-5，本期不建。
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


class WikiDiffTask(Base):
    """知识库差异对比任务 —— 同一需求在两知识库/两版本之间的对比。"""
    __tablename__ = "wiki_diff_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(default="")
    # rag_vs_wiki/wiki_vs_wiki/lanhu_version/external_llm_wiki
    compare_type: Mapped[str] = mapped_column(default="rag_vs_wiki", index=True)
    left_ref_json: Mapped[str] = mapped_column(Text, default="{}")
    right_ref_json: Mapped[str] = mapped_column(Text, default="{}")
    # pending/running/success/failed
    status: Mapped[str] = mapped_column(default="pending", index=True)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")  # 各维度/类型/级别计数
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class WikiDiffItem(Base):
    """差异项 —— 单条差异，带维度/类型/级别/左右值/证据/建议，可转待审 AI 产物。"""
    __tablename__ = "wiki_diff_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(index=True)   # -> wiki_diff_task.id
    project_id: Mapped[int] = mapped_column(index=True)
    # 需求范围/客户端/业务规则/字段/接口/异常路径/权限角色/数据依赖/验收标准/测试覆盖/版本/证据
    dimension: Mapped[str] = mapped_column(default="", index=True)
    # missing_in_left/missing_in_right/conflict/changed/ambiguous/coverage_gap/stale
    diff_type: Mapped[str] = mapped_column(default="", index=True)
    severity: Mapped[str] = mapped_column(default="P2", index=True)  # P0/P1/P2/P3
    title: Mapped[str] = mapped_column(default="")
    left_value: Mapped[str] = mapped_column(Text, default="")
    right_value: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    # pending/accepted/rejected/resolved
    review_status: Mapped[str] = mapped_column(default="pending", index=True)
    resolved_artifact_id: Mapped[int | None] = mapped_column(default=None)  # -> ai_artifact.id
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
