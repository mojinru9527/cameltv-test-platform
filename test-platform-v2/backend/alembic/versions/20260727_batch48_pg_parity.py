"""Batch 48: close PostgreSQL metadata drift without deleting data.

Revision ID: 20260727_batch48_pg_parity
Revises: 20260727_batch48
Create Date: 2026-07-27

This forward-only repair adds columns and indexes omitted by historical
migrations and aligns database nullability with the registered ORM metadata.
Before tightening a nullable column, the migration verifies that no existing
row contains NULL so an invalid deployment stops without changing data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_batch48_pg_parity"
down_revision: Union[str, None] = "20260727_batch48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(connection: sa.Connection, table_name: str) -> bool:
    return table_name in sa.inspect(connection).get_table_names()


def _column_map(
    connection: sa.Connection,
    table_name: str,
) -> dict[str, dict[str, object]]:
    return {
        column["name"]: column
        for column in sa.inspect(connection).get_columns(table_name)
    }


def _index_exists(
    connection: sa.Connection,
    table_name: str,
    index_name: str,
) -> bool:
    return index_name in {
        index["name"] for index in sa.inspect(connection).get_indexes(table_name)
    }


def _ensure_columns(
    connection: sa.Connection,
    table_name: str,
    columns: Sequence[sa.Column[object]],
) -> None:
    if not _table_exists(connection, table_name):
        return
    existing = _column_map(connection, table_name)
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)


def _ensure_index(
    connection: sa.Connection,
    table_name: str,
    index_name: str,
    columns: Sequence[str],
) -> None:
    if not _table_exists(connection, table_name):
        return
    if not _index_exists(connection, table_name, index_name):
        op.create_index(index_name, table_name, list(columns))


def _assert_no_nulls(
    connection: sa.Connection,
    table_name: str,
    column_names: Sequence[str],
) -> None:
    table = sa.table(
        table_name,
        *(sa.column(column_name) for column_name in column_names),
    )
    predicate = sa.or_(
        *(table.c[column_name].is_(None) for column_name in column_names)
    )
    null_rows = connection.execute(
        sa.select(sa.func.count()).select_from(table).where(predicate)
    ).scalar_one()
    if null_rows:
        joined = ", ".join(column_names)
        raise RuntimeError(
            f"{table_name} contains {null_rows} rows with NULL in: {joined}"
        )


def _ensure_not_nullable(
    connection: sa.Connection,
    table_name: str,
    column_names: Sequence[str],
) -> None:
    if not _table_exists(connection, table_name):
        return
    columns = _column_map(connection, table_name)
    targets = [
        column_name
        for column_name in column_names
        if column_name in columns and columns[column_name]["nullable"]
    ]
    if not targets:
        return
    _assert_no_nulls(connection, table_name, targets)
    with op.batch_alter_table(table_name) as batch_op:
        for column_name in targets:
            batch_op.alter_column(
                column_name,
                existing_type=columns[column_name]["type"],
                nullable=False,
            )


def _ensure_requirement_columns(connection: sa.Connection) -> None:
    _ensure_columns(
        connection,
        "api_endpoint",
        (
            sa.Column("remark", sa.Text(), nullable=False, server_default=""),
        ),
    )
    _ensure_columns(
        connection,
        "requirement_document",
        (
            sa.Column("doc_id", sa.String(), nullable=False, server_default=""),
            sa.Column("version", sa.String(), nullable=False, server_default=""),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("diff_json", sa.String(), nullable=False, server_default=""),
            sa.Column(
                "diff_status",
                sa.String(),
                nullable=False,
                server_default="initial",
            ),
        ),
    )
    _ensure_columns(
        connection,
        "test_case",
        (
            sa.Column("api_endpoint_id", sa.Integer(), nullable=True),
            sa.Column("requirement_module_id", sa.Integer(), nullable=True),
        ),
    )

    for table_name, index_name, columns in (
        (
            "requirement_document",
            "ix_requirement_document_doc_id",
            ("doc_id",),
        ),
        (
            "requirement_document",
            "ix_requirement_document_parent_id",
            ("parent_id",),
        ),
        ("test_case", "ix_test_case_api_endpoint_id", ("api_endpoint_id",)),
        (
            "test_case",
            "ix_test_case_requirement_module_id",
            ("requirement_module_id",),
        ),
        ("wiki_review_item", "ix_wiki_review_item_decision", ("decision",)),
    ):
        _ensure_index(connection, table_name, index_name, columns)


def _ensure_model_nullability(connection: sa.Connection) -> None:
    _ensure_not_nullable(
        connection,
        "requirement_review",
        (
            "requirement_id",
            "case_index",
            "case_type",
            "status",
            "edited_data",
            "reviewer_id",
        ),
    )
    _ensure_not_nullable(
        connection,
        "perf_device",
        (
            "device_id",
            "device_name",
            "device_model",
            "platform",
            "os_version",
            "status",
            "last_seen_at",
            "created_at",
        ),
    )
    _ensure_not_nullable(
        connection,
        "perf_metric",
        (
            "session_id",
            "timestamp",
            "elapsed_s",
            "metric_type",
            "data_json",
        ),
    )
    _ensure_not_nullable(
        connection,
        "perf_session",
        (
            "project_id",
            "session_id",
            "device_id",
            "device_name",
            "device_model",
            "platform",
            "pkg_name",
            "metrics",
            "status",
            "duration",
            "actual_duration_s",
            "summary_json",
            "error_message",
            "creator_id",
            "created_at",
            "updated_at",
        ),
    )


def upgrade() -> None:
    connection = op.get_bind()
    _ensure_requirement_columns(connection)
    _ensure_model_nullability(connection)


def downgrade() -> None:
    """Keep the additive PostgreSQL parity repair in place."""
