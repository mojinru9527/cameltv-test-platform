"""Add api_headers/api_body/api_assertions to test_case, gate_status/gate_details/template_id to test_report.

Revision ID: 20260715_test_case_api_cols
Revises: 20260714_lanhu_pg_reconcile
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_test_case_api_cols"
down_revision: Union[str, None] = "20260714_lanhu_pg_reconcile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    test_case_columns = {col["name"] for col in inspector.get_columns("test_case")}
    # ── test_case: API testing columns ──
    with op.batch_alter_table("test_case") as batch_op:
        if "api_headers" not in test_case_columns:
            batch_op.add_column(sa.Column("api_headers", sa.Text(), nullable=False, server_default="{}"))
        if "api_body" not in test_case_columns:
            batch_op.add_column(sa.Column("api_body", sa.Text(), nullable=False, server_default=""))
        if "api_assertions" not in test_case_columns:
            batch_op.add_column(sa.Column("api_assertions", sa.Text(), nullable=False, server_default="[]"))

    # ── test_report: gate columns + template FK ──
    inspector = sa.inspect(op.get_bind())
    report_columns = {col["name"] for col in inspector.get_columns("test_report")}
    report_fks = {fk.get("name") for fk in inspector.get_foreign_keys("test_report")}
    with op.batch_alter_table("test_report") as batch_op:
        if "template_id" not in report_columns:
            batch_op.add_column(sa.Column("template_id", sa.Integer(), nullable=True))
        # Existing local databases may already have template_id from create_all.
        # Avoid forcing a SQLite table rebuild solely to retrofit the FK because
        # reflected JSON text defaults are not portable SQLite constants.
        if "template_id" not in report_columns and "fk_test_report_template_id" not in report_fks:
            batch_op.create_foreign_key("fk_test_report_template_id", "report_template", ["template_id"], ["id"])
        if "gate_status" not in report_columns:
            batch_op.add_column(sa.Column("gate_status", sa.String(20), nullable=True))
        if "gate_details" not in report_columns:
            batch_op.add_column(sa.Column("gate_details", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("test_report") as batch_op:
        batch_op.drop_column("gate_details")
        batch_op.drop_column("gate_status")
        batch_op.drop_constraint("fk_test_report_template_id", type_="foreignkey")
        batch_op.drop_column("template_id")

    with op.batch_alter_table("test_case") as batch_op:
        batch_op.drop_column("api_assertions")
        batch_op.drop_column("api_body")
        batch_op.drop_column("api_headers")
