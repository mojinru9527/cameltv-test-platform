"""Merge the automation worker and external LLM-Wiki revision branches.

Revision ID: 20260713_merge_dual_heads
Revises: 20260713_automation_task_worker, 20260713_external_llm_wiki
Create Date: 2026-07-13
"""

from typing import Sequence, Union


revision: str = "20260713_merge_dual_heads"
down_revision: Union[str, Sequence[str], None] = (
    "20260713_automation_task_worker",
    "20260713_external_llm_wiki",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge point; no schema operations are required."""


def downgrade() -> None:
    """Merge point; no schema operations are required."""
