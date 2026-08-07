"""batch115_ui_job_schedule

Revision ID: 20260807_batch115_ui_schedule
Revises: 20260806_batch106_project_invite
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260807_batch115_ui_schedule"
down_revision: Union[str, None] = "20260806_batch106_project_invite"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # B112-3：UI job 定时 —— schedule 支持 job_type=ui（plan_id 允许为空）
    op.alter_column("test_schedule", "plan_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("test_schedule", sa.Column("job_type", sa.String(length=10), nullable=False, server_default="plan"))
    op.add_column("test_schedule", sa.Column("job_id", sa.Integer(), nullable=True))
    op.create_index("ix_test_schedule_job_id", "test_schedule", ["job_id"])
    # UiTestJob 定时字段
    op.add_column("ui_test_job", sa.Column("cron_expression", sa.String(length=100), nullable=False, server_default=""))
    op.add_column("ui_test_job", sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("ui_test_job", "schedule_enabled")
    op.drop_column("ui_test_job", "cron_expression")
    op.drop_index("ix_test_schedule_job_id", table_name="test_schedule")
    op.drop_column("test_schedule", "job_id")
    op.drop_column("test_schedule", "job_type")
    op.alter_column("test_schedule", "plan_id", existing_type=sa.Integer(), nullable=False)