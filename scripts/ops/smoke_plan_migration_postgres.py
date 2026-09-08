"""Exercise the new migration against disposable PostgreSQL; no production access."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid

from sqlalchemy import create_engine, inspect, text

BACKEND = Path(__file__).resolve().parents[2] / 'test-platform-v2/backend'


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f'Docker {args[0]} failed: exit {result.returncode}')
    return result.stdout.strip()


def main():
    name = f'capacity-pg-{uuid.uuid4().hex[:10]}'
    password = secrets.token_urlsafe(24)
    engine = None
    try:
        docker('run', '-d', '--name', name, '--memory', '256m', '--pids-limit', '128',
               '-p', '127.0.0.1::5432', '-e', f'POSTGRES_PASSWORD={password}',
               '-e', 'POSTGRES_DB=capacity', 'postgres:16-alpine')
        address = docker('port', name, '5432/tcp').splitlines()[0]
        database_url = f'postgresql+psycopg2://postgres:{password}@{address}/capacity'
        engine = create_engine(database_url)
        for attempt in range(30):
            try:
                with engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                break
            except Exception:
                if attempt == 29:
                    raise RuntimeError('Disposable PostgreSQL did not become ready') from None
                time.sleep(1)
        environment = {**os.environ, 'DATABASE_URL': database_url, 'AUTO_CREATE_TABLES': 'false',
                       'PYTHONPATH': str(BACKEND), 'PYTHONIOENCODING': 'utf-8'}

        def migrate(*args):
            result = subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=BACKEND,
                                    env=environment, capture_output=True, text=True, encoding='utf-8', timeout=60)
            if result.returncode:
                raise RuntimeError(f'Migration {args[0]} failed: ' + result.stderr.replace(password, '[redacted]')[-3000:])

        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE capacity_sentinel (id integer PRIMARY KEY, value text NOT NULL)'))
            connection.execute(text("INSERT INTO capacity_sentinel VALUES (1, 'preserved')"))
        migrate('stamp', '20260914_b232_ai_test_lifecycle')
        migrate('upgrade', 'head')
        with engine.begin() as connection:
            assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '20260915_plan_dispatch'
            assert len(inspect(connection).get_columns('plan_execution_job')) == 13
            connection.execute(text("INSERT INTO plan_execution_job (id, project_id, plan_id, creator_id, status, request_json, result_json, error_message, locked_by, created_at) VALUES (1,1,2,3,'pending','{}','{}','','',CURRENT_TIMESTAMP)"))
        # Simulate a previously created table / interrupted revision stamp.
        migrate('stamp', '20260914_b232_ai_test_lifecycle')
        migrate('upgrade', 'head')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM plan_execution_job')) == 1
            assert {i['name'] for i in inspect(connection).get_indexes('plan_execution_job')} == {
                'ix_plan_execution_job_project_id', 'ix_plan_execution_job_plan_id', 'ix_plan_execution_job_status'}
        migrate('downgrade', '20260914_b232_ai_test_lifecycle')
        with engine.connect() as connection:
            assert not inspect(connection).has_table('plan_execution_job')
            assert connection.scalar(text('SELECT value FROM capacity_sentinel')) == 'preserved'
        migrate('upgrade', 'head')
        print(json.dumps({'ok': True, 'postgres': '16-alpine', 'checks': [
            'upgrade', 'columns-and-indexes', 'retry-preserves-jobs', 'downgrade', 'unrelated-data-preserved', 'reupgrade']}))
    finally:
        if engine is not None:
            engine.dispose()
        docker('rm', '-f', '-v', name)


if __name__ == '__main__':
    main()
