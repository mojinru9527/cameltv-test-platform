"""knowledge_vector — 知识切片向量（M2 RAG）

创建 1 张表:
- knowledge_vector: 切片向量（与 knowledge_chunk 1:1，float32 BLOB，dev 存 SQLite，升 PG 切 pgvector）

Revision ID: 20260709_0014
Revises: 20260708_0013
Create Date: 2026-07-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260709_0014"
down_revision: Union[str, None] = "20260708_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "knowledge_vector" not in inspector.get_table_names():
        op.create_table(
            "knowledge_vector",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("chunk_id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("model", sa.String(), nullable=False, server_default=""),
            sa.Column("dim", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("vec", sa.LargeBinary(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    # chunk_id 唯一（1:1）；单独建唯一索引，兼具查询与去重
    indexes = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("knowledge_vector")
        if index.get("name")
    }
    if "ix_knowledge_vector_chunk_id" not in indexes:
        op.create_index(
            "ix_knowledge_vector_chunk_id",
            "knowledge_vector",
            ["chunk_id"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ix_knowledge_vector_chunk_id", table_name="knowledge_vector")
    op.drop_table("knowledge_vector")
