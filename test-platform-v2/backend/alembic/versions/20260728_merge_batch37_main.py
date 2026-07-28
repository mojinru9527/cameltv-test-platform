"""Merge batch37 plan_assignee (develop) into main branch — unify dual heads.

Merges two heads:
  - 20260727_batch48_pg_parity (main)
  - 20260723_batch37_plan_assignee (develop → main via PR #76)

This is a no-op merge revision: both branches have already applied their
changes. It exists solely to give alembic a single head revision so CI
checks pass.

Revision ID: 20260728_merge_batch37_main
Revises: 20260727_batch48_pg_parity, 20260723_batch37_plan_assignee
Create Date: 2026-07-28
"""
from typing import Sequence, Union

revision: str = "20260728_merge_batch37_main"
down_revision: Union[str, Sequence[str], None] = (
    "20260727_batch48_pg_parity",
    "20260723_batch37_plan_assignee",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
