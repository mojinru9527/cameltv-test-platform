"""Merge batch-103 (case quality) + batch-105 (organization) heads.

Batch 103 与 Batch 104/105 均从 20260728_merge_batch37_main 分叉，
本迁移将两条链合并为单头（后合入者解决冲突）。

Revision ID: 20260806_merge_batch103_batch105
Revises: 20260806_batch103_case_quality_fields, 20260806_batch105_organization
Create Date: 2026-08-06
"""
from __future__ import annotations

from alembic import op

revision: str = "20260806_merge_batch103_batch105"
down_revision = (
    "20260806_batch103_case_quality_fields",
    "20260806_batch105_organization",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
