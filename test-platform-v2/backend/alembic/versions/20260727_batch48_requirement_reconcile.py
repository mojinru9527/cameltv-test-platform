"""Batch 48: reconcile requirement-service tables with current metadata.

Revision ID: 20260727_batch48
Revises: 20260726_batch45
Create Date: 2026-07-27

This is a forward-only production repair for databases that were stamped at
the previous head while some ORM columns, constraints, or the API token table
were still absent.  Every operation is guarded so the revision is safe for
both SQLite development databases and PostgreSQL deployments.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_batch48"
down_revision: Union[str, None] = "20260726_batch45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(connection: sa.Connection, table_name: str) -> bool:
    return table_name in sa.inspect(connection).get_table_names()


def _column_names(connection: sa.Connection, table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(connection).get_columns(table_name)
    }


def _index_exists(connection: sa.Connection, table_name: str, index_name: str) -> bool:
    return index_name in {
        index["name"] for index in sa.inspect(connection).get_indexes(table_name)
    }


def _unique_exists(
    connection: sa.Connection,
    table_name: str,
    constraint_name: str,
    columns: Sequence[str],
) -> bool:
    expected_columns = tuple(columns)
    inspector = sa.inspect(connection)
    for constraint in inspector.get_unique_constraints(table_name):
        if constraint.get("name") == constraint_name:
            return True
        if tuple(constraint.get("column_names") or ()) == expected_columns:
            return True
    for index in inspector.get_indexes(table_name):
        if not index.get("unique"):
            continue
        if index.get("name") == constraint_name:
            return True
        if tuple(index.get("column_names") or ()) == expected_columns:
            return True
    return False


def _ensure_unique(
    connection: sa.Connection,
    table_name: str,
    constraint_name: str,
    columns: Sequence[str],
) -> None:
    if _unique_exists(connection, table_name, constraint_name, columns):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.create_unique_constraint(constraint_name, list(columns))


def _keep_latest_duplicate(
    table_name: str,
    columns: Sequence[str],
) -> None:
    """Keep the latest row for an identity before adding its unique guard."""
    identity = ", ".join(columns)
    op.execute(
        sa.text(
            f"DELETE FROM {table_name} "
            f"WHERE id NOT IN (SELECT MAX(id) FROM {table_name} GROUP BY {identity})"
        )
    )


def _ensure_requirement_document(connection: sa.Connection) -> None:
    table_name = "requirement_document"
    if not _table_exists(connection, table_name):
        return

    existing = _column_names(connection, table_name)
    additions = (
        (
            "release_bundle_id",
            sa.Column("release_bundle_id", sa.Integer(), nullable=True),
        ),
        (
            "linked_swagger_id",
            sa.Column("linked_swagger_id", sa.Integer(), nullable=True),
        ),
        (
            "linked_api_endpoint_ids",
            sa.Column(
                "linked_api_endpoint_ids",
                sa.Text(),
                nullable=False,
                server_default="[]",
            ),
        ),
        (
            "extraction_state",
            sa.Column(
                "extraction_state",
                sa.Text(),
                nullable=False,
                server_default="{}",
            ),
        ),
        (
            "extraction_progress",
            sa.Column(
                "extraction_progress",
                sa.Float(),
                nullable=False,
                server_default="0.0",
            ),
        ),
    )
    for column_name, column in additions:
        if column_name not in existing:
            op.add_column(table_name, column)

    index_name = "ix_requirement_document_release_bundle_id"
    if not _index_exists(connection, table_name, index_name):
        op.create_index(index_name, table_name, ["release_bundle_id"])


def _ensure_requirement_module(connection: sa.Connection) -> None:
    table_name = "requirement_module"
    if not _table_exists(connection, table_name):
        return

    existing = _column_names(connection, table_name)
    if "description" not in existing:
        op.add_column(
            table_name,
            sa.Column(
                "description",
                sa.Text(),
                nullable=False,
                server_default="",
            ),
        )
    if "sort_order" not in existing:
        op.add_column(
            table_name,
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def _ensure_test_case(connection: sa.Connection) -> None:
    table_name = "test_case"
    if not _table_exists(connection, table_name):
        return

    if "source_case_index" not in _column_names(connection, table_name):
        op.add_column(
            table_name,
            sa.Column("source_case_index", sa.Integer(), nullable=True),
        )

    _ensure_unique(
        connection,
        table_name,
        "uq_test_case_ai_source_index",
        ("project_id", "source_doc_id", "source_case_index"),
    )
    index_name = "ix_test_case_source_case_index"
    if not _index_exists(connection, table_name, index_name):
        op.create_index(index_name, table_name, ["source_case_index"])


def _ensure_requirement_review(connection: sa.Connection) -> None:
    table_name = "requirement_review"
    if not _table_exists(connection, table_name):
        return

    columns = sa.inspect(connection).get_columns(table_name)
    reviewed_at = next(
        (column for column in columns if column["name"] == "reviewed_at"),
        None,
    )
    if reviewed_at is None:
        op.add_column(
            table_name,
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        )
    needs_nullable_repair = bool(reviewed_at and not reviewed_at["nullable"])
    needs_unique_repair = not _unique_exists(
        connection,
        table_name,
        "uq_requirement_review_case",
        ("requirement_id", "case_type", "case_index"),
    )
    if needs_nullable_repair or needs_unique_repair:
        if needs_unique_repair:
            _keep_latest_duplicate(
                table_name,
                ("requirement_id", "case_type", "case_index"),
            )
        with op.batch_alter_table(table_name) as batch_op:
            if needs_nullable_repair:
                batch_op.alter_column(
                    "reviewed_at",
                    existing_type=sa.DateTime(),
                    nullable=True,
                )
            if needs_unique_repair:
                batch_op.create_unique_constraint(
                    "uq_requirement_review_case",
                    ["requirement_id", "case_type", "case_index"],
                )


def _ensure_module_admin_link(connection: sa.Connection) -> None:
    table_name = "module_admin_link"
    if not _table_exists(connection, table_name):
        return
    if not _unique_exists(
        connection,
        table_name,
        "uq_module_admin_link_identity",
        (
            "project_id",
            "client_module_id",
            "admin_module_id",
            "relation_type",
        ),
    ):
        _keep_latest_duplicate(
            table_name,
            (
                "project_id",
                "client_module_id",
                "admin_module_id",
                "relation_type",
            ),
        )
    _ensure_unique(
        connection,
        table_name,
        "uq_module_admin_link_identity",
        (
            "project_id",
            "client_module_id",
            "admin_module_id",
            "relation_type",
        ),
    )


def _ensure_api_token(connection: sa.Connection) -> None:
    table_name = "api_token"
    if _table_exists(connection, table_name):
        if not _index_exists(connection, table_name, "ix_api_token_project_id"):
            op.create_index(
                "ix_api_token_project_id",
                table_name,
                ["project_id"],
            )
        return
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("token_hash", sa.String(128), nullable=False, server_default=""),
        sa.Column("token_prefix", sa.String(12), nullable=False, server_default=""),
        sa.Column("scopes", sa.String(200), nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_api_token_project_id", table_name, ["project_id"])


def upgrade() -> None:
    connection = op.get_bind()
    _ensure_requirement_document(connection)
    _ensure_requirement_module(connection)
    _ensure_test_case(connection)
    _ensure_requirement_review(connection)
    _ensure_module_admin_link(connection)
    _ensure_api_token(connection)


def downgrade() -> None:
    """Keep the production reconciliation in place.

    The repaired artifacts may have existed before this revision on some
    databases.  Removing them during downgrade would destroy valid schema and
    can lose data, so Batch 48 is intentionally forward-only.
    """
