import io
from pathlib import Path
import runpy

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select, func
from sqlalchemy.pool import StaticPool

from app.models.plan_execution_job import PlanExecutionJob


def migration():
    return runpy.run_path(str(Path(__file__).resolve().parents[2] /
                            'alembic/versions/20260915_plan_dispatch.py'))


def test_migration_creates_model_contract_and_downgrades():
    engine = create_engine('sqlite://', poolclass=StaticPool)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration()['upgrade']()
            inspector = inspect(connection)
            assert {c['name'] for c in inspector.get_columns('plan_execution_job')} == set(PlanExecutionJob.__table__.columns.keys())
            assert {i['name'] for i in inspector.get_indexes('plan_execution_job')} == {
                'ix_plan_execution_job_project_id', 'ix_plan_execution_job_plan_id', 'ix_plan_execution_job_status',
            }
            migration()['downgrade']()
            assert 'plan_execution_job' not in inspect(connection).get_table_names()
    engine.dispose()


def test_postgres_offline_ddl_and_revision_length():
    output = io.StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output})
    with Operations.context(context):
        migration()['upgrade']()
    assert 'CREATE TABLE IF NOT EXISTS plan_execution_job' in output.getvalue()
    assert 'CREATE INDEX IF NOT EXISTS ix_plan_execution_job_status' in output.getvalue()
    assert len(migration()['revision']) <= 32


def test_reconciliation_preserves_auto_created_jobs_and_is_retryable():
    engine = create_engine('sqlite://', poolclass=StaticPool)
    with engine.begin() as connection:
        PlanExecutionJob.__table__.create(connection)
        connection.execute(PlanExecutionJob.__table__.insert().values(project_id=1, plan_id=2, creator_id=3))
        connection.exec_driver_sql('DROP INDEX ix_plan_execution_job_status')
        with Operations.context(MigrationContext.configure(connection)):
            migration()['upgrade']()
            migration()['upgrade']()
        assert connection.scalar(select(func.count()).select_from(PlanExecutionJob)) == 1
        assert 'ix_plan_execution_job_status' in {i['name'] for i in inspect(connection).get_indexes('plan_execution_job')}
    engine.dispose()
