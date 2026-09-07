"""Connect version tasks, classified scenarios, and AITDE run defects.

Revision ID: 20260914_b232_ai_test_lifecycle
Revises: 20260913_b231_traceability_truth
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260914_b232_ai_test_lifecycle"
down_revision: Union[str, None] = "20260913_b231_traceability_truth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _state(table: str) -> tuple[set[str], set[str], dict[tuple[str, ...], str | None]]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set(), set(), {}
    columns = {item["name"] for item in inspector.get_columns(table)}
    indexes = {item["name"] for item in inspector.get_indexes(table)}
    foreign_keys = {
        tuple(item["constrained_columns"]): item["name"]
        for item in inspector.get_foreign_keys(table)
    }
    return columns, indexes, foreign_keys


def upgrade() -> None:
    columns, indexes, foreign_keys = _state("missions")
    if columns and (
        "version_task_id" not in columns
        or "ix_missions_version_task_id" not in indexes
        or ("version_task_id",) not in foreign_keys
    ):
        with op.batch_alter_table("missions") as batch:
            if "version_task_id" not in columns:
                batch.add_column(sa.Column("version_task_id", sa.Integer(), nullable=True))
            if ("version_task_id",) not in foreign_keys:
                batch.create_foreign_key(
                    "fk_missions_version_task_id",
                    "version_task",
                    ["version_task_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "ix_missions_version_task_id" not in indexes:
                batch.create_index("ix_missions_version_task_id", ["version_task_id"])

    columns, indexes, _ = _state("test_scenario_versions")
    missing_columns = {
        "case_type",
        "requirement_role",
        "module_key",
    } - columns
    missing_indexes = {
        "ix_test_scenario_versions_case_type",
        "ix_test_scenario_versions_requirement_role",
    } - indexes
    if columns and (missing_columns or missing_indexes):
        with op.batch_alter_table("test_scenario_versions") as batch:
            if "case_type" in missing_columns:
                batch.add_column(
                    sa.Column(
                        "case_type",
                        sa.String(length=24),
                        nullable=False,
                        server_default="UNCLASSIFIED",
                    )
                )
            if "requirement_role" in missing_columns:
                batch.add_column(
                    sa.Column(
                        "requirement_role",
                        sa.String(length=32),
                        nullable=False,
                        server_default="UNCLASSIFIED",
                    )
                )
            if "module_key" in missing_columns:
                batch.add_column(
                    sa.Column(
                        "module_key", sa.String(length=255), nullable=False, server_default=""
                    )
                )
            if "ix_test_scenario_versions_case_type" in missing_indexes:
                batch.create_index("ix_test_scenario_versions_case_type", ["case_type"])
            if "ix_test_scenario_versions_requirement_role" in missing_indexes:
                batch.create_index(
                    "ix_test_scenario_versions_requirement_role", ["requirement_role"]
                )

    columns, indexes, foreign_keys = _state("defect")
    if columns and (
        "aitde_run_id" not in columns
        or "ix_defect_aitde_run_id" not in indexes
        or ("aitde_run_id",) not in foreign_keys
    ):
        with op.batch_alter_table("defect") as batch:
            if "aitde_run_id" not in columns:
                batch.add_column(sa.Column("aitde_run_id", sa.Integer(), nullable=True))
            if ("aitde_run_id",) not in foreign_keys:
                batch.create_foreign_key(
                    "fk_defect_aitde_run_id",
                    "execution_runs",
                    ["aitde_run_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "ix_defect_aitde_run_id" not in indexes:
                batch.create_index("ix_defect_aitde_run_id", ["aitde_run_id"])


def _drop_columns(
    table: str,
    column_names: tuple[str, ...],
    index_names: tuple[str, ...] = (),
) -> None:
    columns, indexes, foreign_keys = _state(table)
    present_columns = [name for name in column_names if name in columns]
    present_indexes = [name for name in index_names if name in indexes]
    constraints = [
        name
        for constrained_columns, name in foreign_keys.items()
        if name and any(column in constrained_columns for column in present_columns)
    ]
    if not present_columns and not present_indexes:
        return
    with op.batch_alter_table(table) as batch:
        for index_name in present_indexes:
            batch.drop_index(index_name)
        for constraint_name in constraints:
            batch.drop_constraint(constraint_name, type_="foreignkey")
        for column_name in present_columns:
            batch.drop_column(column_name)


def downgrade() -> None:
    _drop_columns("defect", ("aitde_run_id",), ("ix_defect_aitde_run_id",))
    _drop_columns(
        "test_scenario_versions",
        ("module_key", "requirement_role", "case_type"),
        (
            "ix_test_scenario_versions_requirement_role",
            "ix_test_scenario_versions_case_type",
        ),
    )
    _drop_columns("missions", ("version_task_id",), ("ix_missions_version_task_id",))
