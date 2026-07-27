"""Add coverage_threshold, max_failed_cases, max_blocked_cases to quality_gate_config.

Revision ID: 20260709_0015
Revises: 20260709_0014
Create Date: 2026-07-09

R3 quality gate extension: three new optional dimensions (default 0 = disabled).
Backward-compatible: existing configs keep their current behavior unchanged.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260709_0015"
down_revision: Union[str, None] = "20260709_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    """Check if a column already exists (safe for AUTO_CREATE_TABLES=true envs)."""
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "quality_gate_config", "coverage_threshold"):
        op.add_column("quality_gate_config",
            sa.Column("coverage_threshold", sa.Integer(), nullable=False, server_default="0",
                       comment="Minimum requirement coverage % (0-100, 0=disabled)"))

    if not _column_exists(conn, "quality_gate_config", "max_failed_cases"):
        op.add_column("quality_gate_config",
            sa.Column("max_failed_cases", sa.Integer(), nullable=False, server_default="0",
                       comment="Maximum allowed failed cases (0=unlimited)"))

    if not _column_exists(conn, "quality_gate_config", "max_blocked_cases"):
        op.add_column("quality_gate_config",
            sa.Column("max_blocked_cases", sa.Integer(), nullable=False, server_default="0",
                       comment="Maximum allowed blocked cases (0=unlimited)"))


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "quality_gate_config", "max_blocked_cases"):
        op.drop_column("quality_gate_config", "max_blocked_cases")
    if _column_exists(conn, "quality_gate_config", "max_failed_cases"):
        op.drop_column("quality_gate_config", "max_failed_cases")
    if _column_exists(conn, "quality_gate_config", "coverage_threshold"):
        op.drop_column("quality_gate_config", "coverage_threshold")
