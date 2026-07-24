"""Batch 37 — Add assignee_id / due_date to test_plan + source_req_id to test_case.

Revision ID: 20260723_batch37_plan_assignee
Revises: 20260722_batch27_merge_missing
Create Date: 2026-07-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_batch37_plan_assignee"
down_revision: Union[str, None] = "20260722_batch27_merge_missing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    # 1. test_plan: add assignee_id (FK → sys_user)
    existing_tp = {c["name"] for c in insp.get_columns("test_plan")}
    if "assignee_id" not in existing_tp:
        op.add_column(
            "test_plan",
            sa.Column("assignee_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            "ix_test_plan_assignee_id", "test_plan", ["assignee_id"]
        )
    if "due_date" not in existing_tp:
        op.add_column(
            "test_plan",
            sa.Column("due_date", sa.DateTime(), nullable=True),
        )

    # 2. test_case: add source_req_id
    existing_tc = {c["name"] for c in insp.get_columns("test_case")}
    if "source_req_id" not in existing_tc:
        op.add_column(
            "test_case",
            sa.Column(
                "source_req_id", sa.String(), nullable=False, server_default=""
            ),
        )
        op.create_index(
            "ix_test_case_source_req_id", "test_case", ["source_req_id"]
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    existing_tp = {c["name"] for c in insp.get_columns("test_plan")}
    if "assignee_id" in existing_tp:
        op.drop_index("ix_test_plan_assignee_id", table_name="test_plan")
        op.drop_column("test_plan", "assignee_id")
    if "due_date" in existing_tp:
        op.drop_column("test_plan", "due_date")

    existing_tc = {c["name"] for c in insp.get_columns("test_case")}
    if "source_req_id" in existing_tc:
        op.drop_index("ix_test_case_source_req_id", table_name="test_case")
        op.drop_column("test_case", "source_req_id")
