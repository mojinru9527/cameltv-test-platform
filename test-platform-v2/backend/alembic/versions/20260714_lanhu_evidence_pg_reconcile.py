"""Reconcile Lanhu evidence indexes and PostgreSQL server defaults.

Revision ID: 20260714_lanhu_pg_reconcile
Revises: 20260714_lanhu_evidence_quality
Create Date: 2026-07-14

Some deployments historically started the application with
``AUTO_CREATE_TABLES=true`` before Alembic ran.  In that state the guarded
Lanhu table migration sees an existing table and skips the composite indexes,
while ORM-created columns do not have database-side defaults.  This revision
repairs both cases without replacing tables or modifying existing rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_lanhu_pg_reconcile"
down_revision: Union[str, None] = "20260714_lanhu_evidence_quality"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_REQUIRED_INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    (
        "ix_lanhu_evidence_job_project_status",
        "lanhu_evidence_job",
        ["project_id", "status"],
    ),
    (
        "ix_lanhu_evidence_job_project_doc_ver",
        "lanhu_evidence_job",
        ["project_id", "doc_id", "version_id"],
    ),
    (
        "ix_lanhu_evidence_page_job_order",
        "lanhu_evidence_page",
        ["job_id", "order_index"],
    ),
    (
        "ix_lanhu_evidence_page_project_page",
        "lanhu_evidence_page",
        ["project_id", "page_id"],
    ),
    (
        "ix_lanhu_evidence_asset_job_page_type",
        "lanhu_evidence_asset",
        ["job_id", "page_id", "asset_type"],
    ),
)


_POSTGRES_DEFAULTS: tuple[tuple[str, str, sa.types.TypeEngine, object], ...] = (
    ("lanhu_evidence_job", "attempt_no", sa.Integer(), sa.text("1")),
    ("lanhu_evidence_job", "requested_options_json", sa.Text(), sa.text("'{}'")),
    ("lanhu_evidence_job", "import_result_json", sa.Text(), sa.text("'{}'")),
    ("lanhu_evidence_page", "capture_truncated", sa.Boolean(), sa.false()),
    ("lanhu_evidence_page", "review_status", sa.String(length=32), sa.text("'pending'")),
    ("lanhu_evidence_page", "reviewer_id", sa.Integer(), sa.text("0")),
    ("lanhu_evidence_page", "review_comment", sa.Text(), sa.text("''")),
)


def _index_exists(conn, table: str, index: str) -> bool:
    return index in {item["name"] for item in sa.inspect(conn).get_indexes(table)}


def upgrade() -> None:
    conn = op.get_bind()

    for index_name, table_name, columns in _REQUIRED_INDEXES:
        if not _index_exists(conn, table_name, index_name):
            op.create_index(index_name, table_name, columns)

    # SQLite cannot alter a column default without rebuilding the table.  Its
    # fresh migration path already receives these defaults from the preceding
    # quality revision.  PostgreSQL needs this reconciliation for tables that
    # were created by SQLAlchemy before Alembic was enabled.
    if conn.dialect.name == "postgresql":
        for table_name, column_name, column_type, server_default in _POSTGRES_DEFAULTS:
            op.alter_column(
                table_name,
                column_name,
                existing_type=column_type,
                existing_nullable=False,
                server_default=server_default,
            )


def downgrade() -> None:
    """Keep the backwards-compatible repair in place.

    The release plan explicitly forbids schema downgrade for this remediation.
    Removing indexes/defaults would reintroduce the production defect, so this
    reconciliation is intentionally forward-only.
    """
