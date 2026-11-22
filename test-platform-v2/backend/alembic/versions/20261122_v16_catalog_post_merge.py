"""linear post-merge marker for v1.6 catalog + AUD chain

Revision ID: 20261122_v16_catalog_post_merge
Revises: 20261122_merge_v16_catalog_aud

Alembic 的 merge revision 有两个父节点，直接从 merge 执行 `downgrade -1`
会产生 Ambiguous walk。该空 revision 作为单父 head，保证 CI 的
upgrade -> downgrade -1 -> upgrade 可以收敛。
"""
from __future__ import annotations

revision = "20261122_v16_catalog_post_merge"
down_revision = "20261122_merge_v16_catalog_aud"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
