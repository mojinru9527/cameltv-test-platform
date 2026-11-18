"""AUD-019：干扰观测表 + TriageCase 生命周期 + NoiseRule 治理字段

Revision ID: 20261124_aud019_interference
Revises: 20261124_aud014_contract_testcase
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud019_interference"
down_revision = "20261124_aud014_contract_testcase"
branch_labels = None
depends_on = None

_NOISE_COLUMNS = (
    ("environment_id", sa.Integer()),
    ("profile_id", sa.String(length=36)),
    ("detector_key", sa.String(length=120)),
    ("error_class", sa.String(length=80)),
    ("selector_json", sa.JSON()),
    ("app_version", sa.String(length=80)),
    ("evidence_refs_json", sa.JSON()),
    ("approved_by", sa.Integer()),
    ("approved_at", sa.DateTime(timezone=True)),
    ("valid_from", sa.DateTime(timezone=True)),
    ("reason", sa.Text()),
    ("version", sa.Integer()),
    ("matched_count", sa.Integer()),
    ("false_suppress_count", sa.Integer()),
    ("supersedes_id", sa.Integer()),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "noise_rules" in tables:
        existing = {column["name"] for column in inspector.get_columns("noise_rules")}
        for name, type_ in _NOISE_COLUMNS:
            if name in existing:
                continue
            op.add_column("noise_rules", sa.Column(name, type_, nullable=True))
        op.execute("UPDATE noise_rules SET version = 1 WHERE version IS NULL")
        op.execute("UPDATE noise_rules SET matched_count = 0 WHERE matched_count IS NULL")
        op.execute(
            "UPDATE noise_rules SET false_suppress_count = 0 WHERE false_suppress_count IS NULL"
        )

    if "aiqe_interference_observations" not in tables:
        op.create_table(
            "aiqe_interference_observations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.String(length=36), nullable=False),
            sa.Column("node_run_id", sa.String(length=36), nullable=True),
            sa.Column("detector_key", sa.String(length=120), nullable=False),
            sa.Column("detector_version", sa.String(length=40), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("signal_json", sa.JSON(), nullable=True),
            sa.Column("evidence_refs_json", sa.JSON(), nullable=True),
            sa.Column("recommended_experiment", sa.String(length=4), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["run_id"], ["test_runs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["node_run_id"], ["node_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_aiqe_interference_observations_project_id",
            "aiqe_interference_observations",
            ["project_id"],
        )
        op.create_index(
            "ix_aiqe_interference_observations_run_id",
            "aiqe_interference_observations",
            ["run_id"],
        )
        op.create_index(
            "ix_aiqe_interference_observations_detector_key",
            "aiqe_interference_observations",
            ["detector_key"],
        )
        op.create_index(
            "ix_aiqe_interference_run_time",
            "aiqe_interference_observations",
            ["project_id", "run_id", "observed_at"],
        )

    if "aiqe_triage_cases" not in tables:
        op.create_table(
            "aiqe_triage_cases",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.String(length=36), nullable=False),
            sa.Column("node_run_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attribution_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["run_id"], ["test_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_aiqe_triage_cases_project_id", "aiqe_triage_cases", ["project_id"])
        op.create_index("ix_aiqe_triage_cases_run_id", "aiqe_triage_cases", ["run_id"])
        op.create_index("ix_aiqe_triage_cases_status", "aiqe_triage_cases", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for table in ("aiqe_triage_cases", "aiqe_interference_observations"):
        if table in tables:
            op.drop_table(table)
    if "noise_rules" in tables:
        existing = {column["name"] for column in inspector.get_columns("noise_rules")}
        for name, _type in reversed(_NOISE_COLUMNS):
            if name in existing:
                op.drop_column("noise_rules", name)
