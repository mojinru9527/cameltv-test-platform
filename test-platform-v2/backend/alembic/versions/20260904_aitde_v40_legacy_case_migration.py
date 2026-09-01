"""aitde v4.0 legacy cutover: high-value case migration

Revision ID: 20260904_aitde_v40_legacy_case_migration
Revises: 20260904_aitde_v40_legacy_cutover
Create Date: 2026-09-04 02:00:00

V4.0 (V40-005) migration. Creates ``legacy_case_migrations`` — a review-gated
migration of a high-value legacy TestCase to a canonical Scenario. Only a tester
``ACCEPTED`` verdict followed by :meth:`promote` publishes a real scenario, so the
table is the honest audit trail of the legacy case retirement.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260904_aitde_v40_legacy_case_migration"
down_revision: Union[str, None] = "20260904_aitde_v40_legacy_cutover"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "legacy_case_migrations"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE in set(inspector.get_table_names()):
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_case_id", sa.Integer(), nullable=False),
        sa.Column("source_case_key", sa.String(128), nullable=False, server_default=""),
        sa.Column("source_priority", sa.String(4), nullable=False, server_default="P2"),
        sa.Column("destination_mission_id", sa.Integer(), nullable=True),
        sa.Column("contract_version_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draft_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT_PENDING"),
        sa.Column("review_verdict", sa.String(16), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("scenario_id", sa.Integer(), nullable=True),
        sa.Column("scenario_version_id", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_legacy_case_mig_project", _TABLE, ["project_id"])
    op.create_index("ix_legacy_case_mig_source_case", _TABLE, ["source_case_id"])
    op.create_index("ix_legacy_case_mig_priority", _TABLE, ["source_priority"])
    op.create_index("ix_legacy_case_mig_status", _TABLE, ["status"])
    op.create_index("ix_legacy_case_mig_scenario", _TABLE, ["scenario_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in set(inspector.get_table_names()):
        return
    tables = {_TABLE}
    for index in [
        "ix_legacy_case_mig_project",
        "ix_legacy_case_mig_source_case",
        "ix_legacy_case_mig_priority",
        "ix_legacy_case_mig_status",
        "ix_legacy_case_mig_scenario",
    ]:
        existing = {i["name"] for i in inspector.get_indexes(_TABLE)}
        if index in existing:
            op.drop_index(index, table_name=_TABLE)
    op.drop_table(_TABLE)
