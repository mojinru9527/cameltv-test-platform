"""b206_environment_execution_access

Revision ID: 20260828_b206_environment_access
Revises: af68b09103f3
Create Date: 2026-08-28 00:00:00

Batch 206 / C-内网执行器：Environment 加 access_type / execution_mode / runner_key。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260828_b206_environment_access'
down_revision: Union[str, None] = 'af68b09103f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns() -> list[str]:
    conn = op.get_bind()
    return [c['name'] for c in sa.inspect(conn).get_columns('environment')]


def upgrade() -> None:
    cols = _columns()
    if 'access_type' not in cols:
        op.add_column('environment', sa.Column('access_type', sa.String(16), nullable=False, server_default=sa.text("'public'")))
    if 'execution_mode' not in cols:
        op.add_column('environment', sa.Column('execution_mode', sa.String(16), nullable=False, server_default=sa.text("'on_platform'")))
    if 'runner_key' not in cols:
        op.add_column('environment', sa.Column('runner_key', sa.String(64), nullable=False, server_default=sa.text("''")))
    # runner 派发任务表
    op.create_table(
        'runner_execution_task',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), nullable=False, server_default=sa.text('0'), index=True),
        sa.Column('environment_id', sa.Integer(), nullable=False, index=True),
        sa.Column('task_id', sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column('runner_key', sa.String(64), nullable=False, server_default=sa.text("''"), index=True),
        sa.Column('request', sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('assertions', sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column('status', sa.String(16), nullable=False, server_default=sa.text("'pending'"), index=True),
        sa.Column('result', sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('error_message', sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('locked_by', sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_runner_task_pending', 'runner_execution_task', ['status', 'runner_key', 'locked_at'])


def downgrade() -> None:
    op.drop_index('ix_runner_task_pending', table_name='runner_execution_task')
    op.drop_table('runner_execution_task')
    cols = _columns()
    for col in ('runner_key', 'execution_mode', 'access_type'):
        if col in cols:
            op.drop_column('environment', col)
