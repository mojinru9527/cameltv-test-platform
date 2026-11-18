"""AUD-018：Benchmark 数据集 / 执行记录

Revision ID: 20261124_aud018_benchmark
Revises: 20261124_aud019_interference
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud018_benchmark"
down_revision = "20261124_aud019_interference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "aiqe_benchmark_datasets" not in tables:
        op.create_table(
            "aiqe_benchmark_datasets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("dataset_key", sa.String(length=120), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("task_type", sa.String(length=40), nullable=False),
            sa.Column("content_hash", sa.String(length=80), nullable=False),
            sa.Column("sample_count", sa.Integer(), nullable=False),
            sa.Column("gate_eligible", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "dataset_key", "revision", name="uq_aiqe_benchmark_dataset_key_revision"
            ),
        )
        op.create_index(
            "ix_aiqe_benchmark_datasets_project_id", "aiqe_benchmark_datasets", ["project_id"]
        )
        op.create_index(
            "ix_aiqe_benchmark_datasets_dataset_key", "aiqe_benchmark_datasets", ["dataset_key"]
        )
        op.create_index("ix_aiqe_benchmark_datasets_status", "aiqe_benchmark_datasets", ["status"])

    if "aiqe_benchmark_samples" not in tables:
        op.create_table(
            "aiqe_benchmark_samples",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("dataset_id", sa.String(length=36), nullable=False),
            sa.Column("sample_id", sa.String(length=120), nullable=False),
            sa.Column("task_type", sa.String(length=40), nullable=False),
            sa.Column("input_refs_json", sa.JSON(), nullable=True),
            sa.Column("frozen_context_json", sa.JSON(), nullable=True),
            sa.Column("expected_schema_json", sa.JSON(), nullable=True),
            sa.Column("golden_labels_json", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(length=80), nullable=False),
            sa.Column("labeler", sa.String(length=80), nullable=False),
            sa.Column("reviewer", sa.String(length=80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["dataset_id"], ["aiqe_benchmark_datasets.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dataset_id", "sample_id", name="uq_aiqe_benchmark_sample_dataset"),
        )
        op.create_index(
            "ix_aiqe_benchmark_samples_dataset_id", "aiqe_benchmark_samples", ["dataset_id"]
        )

    if "aiqe_benchmark_runs" not in tables:
        op.create_table(
            "aiqe_benchmark_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("dataset_id", sa.String(length=36), nullable=False),
            sa.Column("agent_key", sa.String(length=16), nullable=False),
            sa.Column("agent_version", sa.String(length=40), nullable=False),
            sa.Column("prompt_hash", sa.String(length=80), nullable=False),
            sa.Column("model_provider", sa.String(length=80), nullable=False),
            sa.Column("model_name", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("result_status", sa.String(length=32), nullable=False),
            sa.Column("metrics_json", sa.JSON(), nullable=True),
            sa.Column("per_sample_json", sa.JSON(), nullable=True),
            sa.Column("token_usage_json", sa.JSON(), nullable=True),
            sa.Column("error_text", sa.Text(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["dataset_id"], ["aiqe_benchmark_datasets.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_aiqe_benchmark_runs_dataset_id", "aiqe_benchmark_runs", ["dataset_id"]
        )
        op.create_index("ix_aiqe_benchmark_runs_project_id", "aiqe_benchmark_runs", ["project_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for table in ("aiqe_benchmark_runs", "aiqe_benchmark_samples", "aiqe_benchmark_datasets"):
        if table in tables:
            op.drop_table(table)
