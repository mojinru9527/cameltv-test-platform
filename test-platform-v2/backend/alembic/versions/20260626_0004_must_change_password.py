"""add must_change_password column to sys_user

Revision ID: 20260626_0004
Revises: 20260626_0003
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260626_0004"
down_revision = "20260626_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sys_user",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("sys_user", "must_change_password")
