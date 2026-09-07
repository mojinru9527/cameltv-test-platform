"""Persist asynchronous plan requests independently of HTTP process lifetime."""
from alembic import op
import sqlalchemy as sa

revision = '20260915_plan_dispatch'
down_revision = '20260914_b232_ai_test_lifecycle'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'plan_execution_job',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('request_json', sa.Text(), nullable=False),
        sa.Column('result_json', sa.Text(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('locked_by', sa.String(64), nullable=False),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    for column in ('project_id', 'plan_id', 'status'):
        op.create_index(f'ix_plan_execution_job_{column}', 'plan_execution_job', [column])


def downgrade():
    op.drop_table('plan_execution_job')
