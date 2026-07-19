"""Add managed test-case categories and soft-deletion flags.

Revision ID: 20260715_test_case_categories
Revises: 20260715_add_av_measurements
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_test_case_categories"
down_revision: Union[str, None] = "20260715_add_av_measurements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    test_case_columns = {column["name"] for column in inspector.get_columns("test_case")}
    test_case_indexes = {index["name"] for index in inspector.get_indexes("test_case")}

    if "is_deleted" not in test_case_columns:
        with op.batch_alter_table("test_case") as batch_op:
            batch_op.add_column(
                sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false())
            )
    if "ix_test_case_is_deleted" not in test_case_indexes:
        op.create_index("ix_test_case_is_deleted", "test_case", ["is_deleted"])

    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())
    if "test_case_domain" not in existing_tables:
        op.create_table(
            "test_case_domain",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "project_id", "name", name="uq_test_case_domain_project_name"
            ),
        )
        op.create_index("ix_test_case_domain_project_id", "test_case_domain", ["project_id"])
        op.create_index("ix_test_case_domain_is_deleted", "test_case_domain", ["is_deleted"])

    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())
    if "test_case_module" not in existing_tables:
        op.create_table(
            "test_case_module",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("domain_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["domain_id"], ["test_case_domain.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint(
                "domain_id", "name", name="uq_test_case_module_domain_name"
            ),
        )
        op.create_index("ix_test_case_module_project_id", "test_case_module", ["project_id"])
        op.create_index("ix_test_case_module_domain_id", "test_case_module", ["domain_id"])
        op.create_index("ix_test_case_module_is_deleted", "test_case_module", ["is_deleted"])

    # Backfill managed categories from all existing, non-empty case values.
    op.execute(
        sa.text(
            """
            INSERT INTO test_case_domain
                (project_id, name, is_deleted, created_at, updated_at)
            SELECT DISTINCT project_id, domain, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM test_case
            WHERE domain IS NOT NULL AND TRIM(domain) <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM test_case_domain d
                  WHERE d.project_id = test_case.project_id AND d.name = test_case.domain
              )
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO test_case_module
                (project_id, domain_id, name, is_deleted, created_at, updated_at)
            SELECT DISTINCT tc.project_id, d.id, tc.module, false,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM test_case tc
            JOIN test_case_domain d
              ON d.project_id = tc.project_id AND d.name = tc.domain
            WHERE tc.module IS NOT NULL AND TRIM(tc.module) <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM test_case_module m
                  WHERE m.domain_id = d.id AND m.name = tc.module
              )
            """
        )
    )

    # API cases are managed by the dedicated API testing module. Keep their
    # case rows intact while hiding the legacy category from case services.
    op.execute(
        sa.text(
            """
            UPDATE test_case_module
            SET is_deleted = true, updated_at = CURRENT_TIMESTAMP
            WHERE domain_id IN (
                SELECT id FROM test_case_domain WHERE name = '接口测试'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE test_case_domain
            SET is_deleted = true, updated_at = CURRENT_TIMESTAMP
            WHERE name = '接口测试'
            """
        )
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())
    if "test_case_module" in existing_tables:
        op.drop_table("test_case_module")
    if "test_case_domain" in existing_tables:
        op.drop_table("test_case_domain")

    test_case_columns = {column["name"] for column in inspector.get_columns("test_case")}
    if "is_deleted" in test_case_columns:
        with op.batch_alter_table("test_case") as batch_op:
            batch_op.drop_column("is_deleted")
