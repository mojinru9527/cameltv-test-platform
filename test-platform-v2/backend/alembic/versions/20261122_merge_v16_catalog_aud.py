"""merge v1.6 catalog branch with v1.5 AUD / PR595 execution branch

Revision ID: 20261122_merge_v16_catalog_aud
Revises: 20261120_v16_014_catalog, 20261125_merge_aud_v15_pr595

没有结构变更，仅收敛 v1.6 catalog 与 AUD 链路的两个 head。
"""
from __future__ import annotations

revision = "20261122_merge_v16_catalog_aud"
down_revision = (
    "20261120_v16_014_catalog",
    "20261125_merge_aud_v15_pr595",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
