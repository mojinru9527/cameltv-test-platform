"""batch104_add_invite_code

Revision ID: 20260806_batch104_invite_code
Revises: 20260728_merge_batch37_main
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260806_batch104_invite_code"
down_revision: Union[str, None] = "20260728_merge_batch37_main"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "sys_invite_code" in inspector.get_table_names():
        return
    op.create_table(
        "sys_invite_code",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sys_invite_code_code", "sys_invite_code", ["code"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "sys_invite_code" in inspector.get_table_names():
        op.drop_index("ix_sys_invite_code_code", table_name="sys_invite_code")
        op.drop_table("sys_invite_code")
