"""AUD-014/015：Requirement Contract + 结构化 TestCase

Revision ID: 20261124_aud014_contract_testcase
Revises: 20261124_aud013_agent_protocol
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261124_aud014_contract_testcase"
down_revision = "20261124_aud013_agent_protocol"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "aiqe_requirement_contracts" not in tables:
        op.create_table(
            "aiqe_requirement_contracts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("requirement_id", sa.String(length=80), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("business_goal", sa.Text(), nullable=False),
            sa.Column("actors_json", sa.JSON(), nullable=True),
            sa.Column("business_rules_json", sa.JSON(), nullable=True),
            sa.Column("ambiguities_json", sa.JSON(), nullable=True),
            sa.Column("assumptions_json", sa.JSON(), nullable=True),
            sa.Column("conflicts_json", sa.JSON(), nullable=True),
            sa.Column("nfr_json", sa.JSON(), nullable=True),
            sa.Column("source_refs_json", sa.JSON(), nullable=True),
            sa.Column("revision_checksum", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "project_id", "requirement_id", "revision", name="uq_aiqe_contracts_req_revision"
            ),
        )
        op.create_index(
            "ix_aiqe_requirement_contracts_project_id",
            "aiqe_requirement_contracts",
            ["project_id"],
        )
        op.create_index(
            "ix_aiqe_requirement_contracts_requirement_id",
            "aiqe_requirement_contracts",
            ["requirement_id"],
        )
        op.create_index(
            "ix_aiqe_requirement_contracts_status", "aiqe_requirement_contracts", ["status"]
        )
        op.create_index(
            "ix_aiqe_contracts_project_status",
            "aiqe_requirement_contracts",
            ["project_id", "status"],
        )

    if "aiqe_acceptance_criteria" not in tables:
        op.create_table(
            "aiqe_acceptance_criteria",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("contract_id", sa.String(length=36), nullable=False),
            sa.Column("ac_id", sa.String(length=40), nullable=False),
            sa.Column("given", sa.Text(), nullable=False),
            sa.Column("when", sa.Text(), nullable=False),
            sa.Column("then_json", sa.JSON(), nullable=True),
            sa.Column("priority", sa.String(length=4), nullable=False),
            sa.Column("oracle_type", sa.String(length=40), nullable=False),
            sa.Column("oracle_ref", sa.String(length=160), nullable=False),
            sa.Column("oracle_revision", sa.Integer(), nullable=True),
            sa.Column("platforms_json", sa.JSON(), nullable=True),
            sa.Column("approval_status", sa.String(length=20), nullable=False),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["contract_id"], ["aiqe_requirement_contracts.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("contract_id", "ac_id", name="uq_aiqe_ac_contract_ac"),
        )
        op.create_index(
            "ix_aiqe_acceptance_criteria_contract_id", "aiqe_acceptance_criteria", ["contract_id"]
        )

    if "aiqe_test_cases" not in tables:
        op.create_table(
            "aiqe_test_cases",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("case_id", sa.String(length=80), nullable=False),
            sa.Column("scenario_id", sa.String(length=80), nullable=False),
            sa.Column("contract_id", sa.String(length=36), nullable=True),
            sa.Column("contract_revision", sa.Integer(), nullable=True),
            sa.Column("covers_ac_ids_json", sa.JSON(), nullable=True),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("priority", sa.String(length=4), nullable=False),
            sa.Column("preconditions_json", sa.JSON(), nullable=True),
            sa.Column("fixtures_json", sa.JSON(), nullable=True),
            sa.Column("platform_targets_json", sa.JSON(), nullable=True),
            sa.Column("steps_json", sa.JSON(), nullable=True),
            sa.Column("cleanup_json", sa.JSON(), nullable=True),
            sa.Column("oracle_type", sa.String(length=40), nullable=False),
            sa.Column("oracle_ref", sa.String(length=160), nullable=False),
            sa.Column("automation_grade", sa.String(length=1), nullable=False),
            sa.Column("review_status", sa.String(length=20), nullable=False),
            sa.Column("dedupe_key", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["sys_project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["contract_id"], ["aiqe_requirement_contracts.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("project_id", "case_id", name="uq_aiqe_cases_project_case"),
        )
        op.create_index("ix_aiqe_test_cases_project_id", "aiqe_test_cases", ["project_id"])
        op.create_index("ix_aiqe_test_cases_case_id", "aiqe_test_cases", ["case_id"])
        op.create_index("ix_aiqe_test_cases_dedupe_key", "aiqe_test_cases", ["dedupe_key"])
        op.create_index(
            "ix_aiqe_cases_contract", "aiqe_test_cases", ["contract_id", "contract_revision"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for table in ("aiqe_test_cases", "aiqe_acceptance_criteria", "aiqe_requirement_contracts"):
        if table in tables:
            op.drop_table(table)
