"""external_llm_wiki — VNext-5 外部 LLM-Wiki 连接器表

创建 1 张表:
- external_wiki_connection: 外部 LLM Wiki Desktop/API 连接配置（项目级隔离，token 加密存储）

Revision ID: 20260713_external_llm_wiki
Revises: 20260713_ui_runner
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_external_llm_wiki"
down_revision: Union[str, None] = "20260713_ui_runner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard: table may already exist from SQLAlchemy auto-create on startup
    from sqlalchemy import inspect as sa_inspect
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    if "external_wiki_connection" not in inspector.get_table_names():
        op.create_table(
            "external_wiki_connection",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("name", sa.String(200), nullable=False, server_default=""),
            sa.Column("provider", sa.String(50), nullable=False, server_default="llm_wiki_desktop"),
            sa.Column("base_url", sa.String(500), nullable=False, server_default=""),
            sa.Column("token_encrypted", sa.Text(), nullable=True),
            sa.Column("external_project_id", sa.String(200), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("external_wiki_connection")
