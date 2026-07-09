"""knowledge_base — 知识中心基础表

创建 6 张表:
- knowledge_source: 知识源（原始资料）
- knowledge_chunk: 知识切片（RAG 检索最小单位）
- knowledge_entity: 知识图谱节点（M3 使用，本期建表）
- knowledge_relation: 知识图谱边（M3 使用，本期建表）
- ai_artifact: AI 生成草稿（进审核台）
- agent_run: Agent 执行记录

Revision ID: 20260708_0013
Revises: 20260707_0012
Create Date: 2026-07-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260708_0013"
down_revision: Union[str, None] = "20260707_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # knowledge_source
    op.create_table(
        "knowledge_source",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_type", sa.String(), nullable=False, server_default="manual", index=True),
        sa.Column("source_id", sa.Integer(), nullable=True, index=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("source_ref", sa.String(), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("version", sa.String(), nullable=False, server_default=""),
        sa.Column("iteration_id", sa.Integer(), nullable=True, index=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("raw_content", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # knowledge_chunk
    op.create_table(
        "knowledge_chunk",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_id", sa.Integer(), nullable=False, index=True),
        sa.Column("chunk_type", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_id", sa.String(), nullable=False, server_default=""),
        sa.Column("tags", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(), nullable=False, server_default="active", index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # knowledge_entity (M3 使用，本期建空表)
    op.create_table(
        "knowledge_entity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("entity_type", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("entity_key", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("business_ref_type", sa.String(), nullable=False, server_default=""),
        sa.Column("business_ref_id", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # knowledge_relation (M3 使用，本期建空表)
    op.create_table(
        "knowledge_relation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("from_entity_id", sa.Integer(), nullable=False, index=True),
        sa.Column("relation_type", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("to_entity_id", sa.Integer(), nullable=False, index=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_chunk_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ai_artifact
    op.create_table(
        "ai_artifact",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("artifact_type", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("content_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("source_refs", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("agent_run_id", sa.Integer(), nullable=True, index=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("review_status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("imported_ref_type", sa.String(), nullable=False, server_default=""),
        sa.Column("imported_ref_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # agent_run
    op.create_table(
        "agent_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("agent_type", sa.String(), nullable=False, server_default="", index=True),
        sa.Column("trigger_type", sa.String(), nullable=False, server_default="manual"),
        sa.Column("input_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("retrieved_context_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("output_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending", index=True),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("operator_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("agent_run")
    op.drop_table("ai_artifact")
    op.drop_table("knowledge_relation")
    op.drop_table("knowledge_entity")
    op.drop_table("knowledge_chunk")
    op.drop_table("knowledge_source")
