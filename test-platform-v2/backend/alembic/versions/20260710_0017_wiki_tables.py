"""wiki_tables — LLM-Wiki 知识库差异对比能力（VNext-1..3）

创建 6 张表:
- wiki_raw_source: 原始来源（事实层，可 supersede，可绑 knowledge_source）
- wiki_page:       LLM 编译的结构化 Wiki 页面（带来源引用与审核状态）
- wiki_link:       Wiki 页面级链接
- wiki_ingest_job: 两阶段 Wiki 编译任务状态
- wiki_diff_task:  知识库差异对比任务
- wiki_diff_item:  单条差异项（可转待审 AI 产物）

wiki_external_connection（VNext-5）本期不建。

Revision ID: 20260710_0017
Revises: 20260710_0016
Create Date: 2026-07-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260710_0017"
down_revision: Union[str, None] = "20260710_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())

    def create_table_if_missing(table_name: str, *columns) -> None:
        if table_name not in tables:
            op.create_table(table_name, *columns)

    create_table_if_missing(
        "wiki_raw_source",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_type", sa.String(), nullable=False, server_default="lanhu", index=True),
        sa.Column("source_ref", sa.String(), nullable=False, server_default=""),
        sa.Column("business_ref_type", sa.String(), nullable=False, server_default=""),
        sa.Column("business_ref_id", sa.Integer(), nullable=True, index=True),
        sa.Column("knowledge_source_id", sa.Integer(), nullable=True, index=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("immutable_version", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="active", index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    create_table_if_missing(
        "wiki_page",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("wiki_space_id", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("page_type", sa.String(), nullable=False, server_default="requirement", index=True),
        sa.Column("slug", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("frontmatter_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("source_refs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("content_hash", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_by_agent_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    create_table_if_missing(
        "wiki_link",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("from_page_id", sa.Integer(), nullable=False, index=True),
        sa.Column("to_page_id", sa.Integer(), nullable=False, index=True),
        sa.Column("link_type", sa.String(), nullable=False, server_default="mentions", index=True),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    create_table_if_missing(
        "wiki_ingest_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("raw_source_id", sa.Integer(), nullable=False, index=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("stage", sa.String(), nullable=False, server_default="analysis"),
        sa.Column("analysis_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("operator_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    create_table_if_missing(
        "wiki_diff_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("compare_type", sa.String(), nullable=False, server_default="rag_vs_wiki", index=True),
        sa.Column("left_ref_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("right_ref_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    create_table_if_missing(
        "wiki_diff_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("dimension", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("diff_type", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("severity", sa.String(), nullable=False, server_default="P2", index=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("left_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("right_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("suggestion", sa.Text(), nullable=False, server_default=""),
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("resolved_artifact_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("wiki_diff_item")
    op.drop_table("wiki_diff_task")
    op.drop_table("wiki_ingest_job")
    op.drop_table("wiki_link")
    op.drop_table("wiki_page")
    op.drop_table("wiki_raw_source")
