"""AUD-009/010：部署证明 + 回归请求/对比快照

Revision ID: 20261124_aud009_regression_hardening
Revises: 20261124_aud008_artifact_lifecycle
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud009_regression_hardening"
down_revision = "20261124_aud008_artifact_lifecycle"
branch_labels = None
depends_on = None

_REGRESSION_COLUMNS = (
    ("idempotency_fingerprint", sa.String(length=64)),
    ("deployed_sha", sa.String(length=64)),
    ("target_environment_id", sa.Integer()),
    ("source_run_id", sa.String(length=36)),
    ("workflow_definition_id", sa.String(length=36)),
    ("workflow_checksum", sa.String(length=128)),
    ("profile_checksum", sa.String(length=128)),
    ("scope", sa.String(length=40)),
    ("scope_hash", sa.String(length=64)),
    ("mandatory_case_ids_json", sa.JSON()),
    ("selected_case_ids_json", sa.JSON()),
    ("excluded_json", sa.JSON()),
    ("reason", sa.Text()),
    ("request_idempotency_key", sa.String(length=128)),
    ("blockers_json", sa.JSON()),
    ("completed_at", sa.DateTime(timezone=True)),
    ("terminal_summary_json", sa.JSON()),
    ("failing_case_ids_json", sa.JSON()),
    ("assertion_refs_json", sa.JSON()),
    ("evidence_refs_json", sa.JSON()),
    ("comparison_snapshot_id", sa.String(length=36)),
    ("suggestion", sa.String(length=32)),
    ("cancelled_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "defect_regressions" in tables:
        existing = {column["name"] for column in inspector.get_columns("defect_regressions")}
        for name, type_ in _REGRESSION_COLUMNS:
            if name in existing:
                continue
            op.add_column("defect_regressions", sa.Column(name, type_, nullable=True))
        indexes = {index["name"] for index in inspector.get_indexes("defect_regressions")}
        if "ix_defect_regressions_idempotency_fingerprint" not in indexes:
            op.create_index(
                "ix_defect_regressions_idempotency_fingerprint",
                "defect_regressions",
                ["idempotency_fingerprint"],
                unique=True,
            )
        if "ix_defect_regressions_source_run_id" not in indexes:
            op.create_index(
                "ix_defect_regressions_source_run_id", "defect_regressions", ["source_run_id"]
            )

    if "aiqe_deployment_attestations" not in tables:
        op.create_table(
            "aiqe_deployment_attestations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("environment_id", sa.Integer(), nullable=True),
            sa.Column("commit_sha", sa.String(length=64), nullable=False),
            sa.Column("image_digest", sa.String(length=128), nullable=False),
            sa.Column("source", sa.String(length=20), nullable=False),
            sa.Column("evidence_ref", sa.String(length=255), nullable=False),
            sa.Column("attested_by", sa.Integer(), nullable=True),
            sa.Column("attested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["environment_id"], ["environment.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["attested_by"], ["sys_user.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        for index, columns in (
            ("ix_aiqe_deployment_attestations_project_id", ["project_id"]),
            ("ix_aiqe_deployment_attestations_environment_id", ["environment_id"]),
            ("ix_aiqe_deployment_attestations_commit_sha", ["commit_sha"]),
            (
                "ix_aiqe_deployment_attestations_env_sha",
                ["project_id", "environment_id", "commit_sha"],
            ),
        ):
            op.create_index(index, "aiqe_deployment_attestations", columns)

    if "run_comparison_snapshots" not in tables:
        op.create_table(
            "run_comparison_snapshots",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("regression_id", sa.Integer(), nullable=True),
            sa.Column("defect_id", sa.Integer(), nullable=True),
            sa.Column("source_run_id", sa.String(length=36), nullable=True),
            sa.Column("regression_run_id", sa.String(length=36), nullable=True),
            sa.Column("fixed_sha", sa.String(length=64), nullable=False),
            sa.Column("deployed_sha", sa.String(length=64), nullable=False),
            sa.Column("workflow_checksum", sa.String(length=128), nullable=True),
            sa.Column("outcome", sa.String(length=24), nullable=False),
            sa.Column("assertion_diff_json", sa.JSON(), nullable=True),
            sa.Column("node_attempt_diff_json", sa.JSON(), nullable=True),
            sa.Column("evidence_refs_json", sa.JSON(), nullable=True),
            sa.Column("new_failures_json", sa.JSON(), nullable=True),
            sa.Column("fixed_failures_json", sa.JSON(), nullable=True),
            sa.Column("blocked_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for index, columns in (
            ("ix_run_comparison_snapshots_project_id", ["project_id"]),
            ("ix_run_comparison_snapshots_regression_id", ["regression_id"]),
            ("ix_run_comparison_snapshots_defect_id", ["defect_id"]),
        ):
            op.create_index(index, "run_comparison_snapshots", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "run_comparison_snapshots" in tables:
        op.drop_table("run_comparison_snapshots")
    if "aiqe_deployment_attestations" in tables:
        op.drop_table("aiqe_deployment_attestations")
    if "defect_regressions" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("defect_regressions")}
        for index in (
            "ix_defect_regressions_source_run_id",
            "ix_defect_regressions_idempotency_fingerprint",
        ):
            if index in indexes:
                op.drop_index(index, table_name="defect_regressions")
        existing = {column["name"] for column in inspector.get_columns("defect_regressions")}
        for name, _type in reversed(_REGRESSION_COLUMNS):
            if name in existing:
                op.drop_column("defect_regressions", name)
