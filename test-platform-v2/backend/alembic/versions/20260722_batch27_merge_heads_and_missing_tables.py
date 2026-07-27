"""batch27_merge_heads_and_missing_tables — Merge heads + add wiki_lint tables, knowledge_iteration, knowledge_snapshot.

Merges three heads:
  - 20260719_perf_tables
  - 20260721_knowledge_module_name
  - 20260722_b27_knowledge_sphere

Adds 4 missing tables:
  - wiki_lint_report: Wiki 健康体检报告
  - wiki_lint_issue: 单条 lint 问题
  - knowledge_iteration: 迭代知识包
  - knowledge_snapshot: 知识快照

Revision ID: 20260722_batch27_merge_missing
Revises: 20260719_perf_tables, 20260721_knowledge_module_name, 20260722_b27_knowledge_sphere
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_batch27_merge_missing"
down_revision: Union[str, tuple[str, ...], None] = (
    "20260719_perf_tables",
    "20260721_knowledge_module_name",
    "20260722_b27_knowledge_sphere",
)
branch_labels: Union[str, Sequence[str], None] = ("batch27",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    # ── wiki_lint_report ──
    if "wiki_lint_report" not in existing:
        op.create_table(
            "wiki_lint_report",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("status", sa.String(), nullable=False, server_default="running", index=True),
            sa.Column("summary_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── wiki_lint_issue ──
    if "wiki_lint_issue" not in existing:
        op.create_table(
            "wiki_lint_issue",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("report_id", sa.Integer(), nullable=False, index=True),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("rule", sa.String(), nullable=False, server_default="", index=True),
            sa.Column("severity", sa.String(), nullable=False, server_default="P2", index=True),
            sa.Column("title", sa.String(), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("entity_type", sa.String(), nullable=False, server_default=""),
            sa.Column("entity_id", sa.Integer(), nullable=True, index=True),
            sa.Column("related_entity_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("suggestion", sa.Text(), nullable=False, server_default=""),
            sa.Column("review_status", sa.String(), nullable=False, server_default="pending", index=True),
            sa.Column("resolved_artifact_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── knowledge_iteration ──
    if "knowledge_iteration" not in existing:
        op.create_table(
            "knowledge_iteration",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False, index=True),
            sa.Column("iteration_name", sa.String(), nullable=False, server_default=""),
            sa.Column("version", sa.String(), nullable=False, server_default=""),
            sa.Column("start_date", sa.DateTime(), nullable=True),
            sa.Column("end_date", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="active", index=True),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── knowledge_snapshot ──
    if "knowledge_snapshot" not in existing:
        op.create_table(
            "knowledge_snapshot",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("iteration_id", sa.Integer(), nullable=False, index=True),
            sa.Column("snapshot_type", sa.String(), nullable=False, server_default="", index=True),
            sa.Column("data_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("knowledge_snapshot")
    op.drop_table("knowledge_iteration")
    op.drop_table("wiki_lint_issue")
    op.drop_table("wiki_lint_report")
