"""batch106_add_project_invite

Revision ID: 20260806_batch106_project_invite
Revises: 20260806_batch105_organization
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260806_batch106_project_invite"
down_revision: Union[str, None] = "20260806_merge_batch103_batch105"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "sys_project_invite" in inspector.get_table_names():
        return
    op.create_table(
        "sys_project_invite",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sys_project_invite_project_id", "sys_project_invite", ["project_id"])
    op.create_index("ix_sys_project_invite_token", "sys_project_invite", ["token"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "sys_project_invite" in inspector.get_table_names():
        op.drop_table("sys_project_invite")
