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


def upgrade() -> None:
    with op.batch_alter_table("missions") as batch:
        batch.add_column(sa.Column("version_task_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_missions_version_task_id",
            "version_task",
            ["version_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_missions_version_task_id", ["version_task_id"])

    with op.batch_alter_table("test_scenario_versions") as batch:
        batch.add_column(
            sa.Column(
                "case_type", sa.String(length=24), nullable=False,
                server_default="UNCLASSIFIED",
            )
        )
        batch.add_column(
            sa.Column(
                "requirement_role", sa.String(length=32), nullable=False,
                server_default="UNCLASSIFIED",
            )
        )
        batch.add_column(
            sa.Column("module_key", sa.String(length=255), nullable=False, server_default="")
        )
        batch.create_index("ix_test_scenario_versions_case_type", ["case_type"])
        batch.create_index(
            "ix_test_scenario_versions_requirement_role", ["requirement_role"]
        )

    with op.batch_alter_table("defect") as batch:
        batch.add_column(sa.Column("aitde_run_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_defect_aitde_run_id",
            "execution_runs",
            ["aitde_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_defect_aitde_run_id", ["aitde_run_id"])


def downgrade() -> None:
    with op.batch_alter_table("defect") as batch:
        batch.drop_index("ix_defect_aitde_run_id")
        batch.drop_constraint("fk_defect_aitde_run_id", type_="foreignkey")
        batch.drop_column("aitde_run_id")

    with op.batch_alter_table("test_scenario_versions") as batch:
        batch.drop_index("ix_test_scenario_versions_requirement_role")
        batch.drop_index("ix_test_scenario_versions_case_type")
        batch.drop_column("module_key")
        batch.drop_column("requirement_role")
        batch.drop_column("case_type")

    with op.batch_alter_table("missions") as batch:
        batch.drop_index("ix_missions_version_task_id")
        batch.drop_constraint("fk_missions_version_task_id", type_="foreignkey")
        batch.drop_column("version_task_id")
