from datetime import timedelta
import json
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.task_queue import atomic_claim, reap_stale, utcnow
from app.models.plan_execution_job import PlanExecutionJob
from app.models.test_plan import TestPlan as Plan
from app.services import plan_execution_queue as queue


@pytest.fixture
def pending(db_session, monkeypatch):
    monkeypatch.setattr(settings, 'worker_execution_enabled', True)
    monkeypatch.setattr(queue, 'SessionLocal', sessionmaker(bind=db_session.get_bind()))
    plan = Plan(project_id=1, name='dispatch')
    db_session.add(plan)
    db_session.commit()
    job_id = queue.enqueue(db_session, plan_id=plan.id, project_id=1, executor_id=1,
                           environment_id=None, ui_environment_id=None, auto_ui=False)
    return job_id


def test_pending_survives_session_close_and_executes_once(pending, db_session):
    db_session.close()
    queue.poll_once()
    queue.poll_once()
    row = db_session.get(PlanExecutionJob, pending)
    assert row.status == 'completed'
    assert json.loads(row.result_json)['total'] == 0
    assert row.started_at is not None and row.finished_at is not None
    assert row.locked_by == ''


def test_claim_is_exclusive_and_lost_running_work_is_not_replayed(pending, db_session):
    row = atomic_claim(db_session, queue.SPEC, worker_id='one')
    assert row.id == pending
    assert atomic_claim(db_session, queue.SPEC, worker_id='two') is None
    row.locked_at = utcnow() - timedelta(hours=1)
    db_session.commit()
    assert reap_stale(db_session, queue.SPEC) == 1
    assert atomic_claim(db_session, queue.SPEC, worker_id='three') is None
    db_session.expire_all()
    assert db_session.get(PlanExecutionJob, pending).status == 'failed'


def test_failure_is_visible_and_not_automatically_retried(pending, db_session, monkeypatch):
    execute = Mock(side_effect=RuntimeError('test execution failure'))
    monkeypatch.setattr('app.services.test_plan_service.execute_all_cases', execute)
    queue.poll_once()
    queue.poll_once()
    row = db_session.get(PlanExecutionJob, pending)
    assert row.status == 'failed'
    assert row.error_message == 'test execution failure'
    assert execute.call_count == 1


def test_api_never_claims_and_status_is_project_scoped(pending, db_session, monkeypatch):
    monkeypatch.setattr(settings, 'worker_execution_enabled', False)
    queue.poll_once()
    row = db_session.get(PlanExecutionJob, pending)
    assert row.status == 'pending'
    assert queue.list_jobs(db_session, row.plan_id, 2) == []
    assert queue.list_jobs(db_session, row.plan_id, 1)[0]['id'] == pending


def test_missing_or_foreign_plan_is_not_accepted(db_session):
    with pytest.raises(ValueError):
        queue.enqueue(db_session, plan_id=999, project_id=1, executor_id=1,
                      environment_id=None, ui_environment_id=None, auto_ui=False)


def test_pending_request_consumed_once_across_fresh_processes(tmp_path):
    import os
    import subprocess
    import sys
    from sqlalchemy import create_engine
    from app.core.db import Base

    url = 'sqlite:///' + (tmp_path / 'plans.db').as_posix()
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        plan = Plan(project_id=1, name='process restart')
        db.add(plan)
        db.commit()
        job_id = queue.enqueue(db, plan_id=plan.id, project_id=1, executor_id=1,
                               environment_id=None, ui_environment_id=None, auto_ui=False)
    marker = tmp_path / 'executions.txt'
    source = '''
import sys
from pathlib import Path
import app.models
from app.services import test_plan_service, plan_execution_queue
original = test_plan_service.execute_all_cases
def execute(*args, **kwargs):
    path = Path(sys.argv[1])
    path.write_text((path.read_text() if path.exists() else '') + 'executed\\n')
    return original(*args, **kwargs)
test_plan_service.execute_all_cases = execute
plan_execution_queue.poll_once()
'''
    env = {**os.environ, 'DATABASE_URL': url, 'WORKER_EXECUTION_ENABLED': 'true'}
    for _ in range(2):
        result = subprocess.run([sys.executable, '-c', source, str(marker)], env=env,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
    assert marker.read_text().splitlines() == ['executed']
    with factory() as db:
        assert db.get(PlanExecutionJob, job_id).status == 'completed'
    engine.dispose()


def test_http_job_status_and_missing_plan_contract(pending, db_session, client, auth_headers):
    from app.models.project import Project
    row = db_session.get(PlanExecutionJob, pending)
    response = client.get(f'/api/v1/test-plans/{row.plan_id}/execution-jobs', headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['data'][0]['status'] == 'pending'
    db_session.add(Project(id=2, code='OTHER-DISPATCH', name='Other project'))
    db_session.commit()
    other = client.get(f'/api/v1/test-plans/{row.plan_id}/execution-jobs',
                       headers={**auth_headers, 'X-Project-Id': '2'})
    assert other.json()['data'] == []
    missing = client.post('/api/v1/test-plans/99999/execute-all', headers=auth_headers,
                          json={'async_mode': True})
    assert missing.status_code == 200 and missing.json()['code'] == 404


def test_async_submission_survives_runner_outage(pending, db_session, client, auth_headers, monkeypatch):
    row = db_session.get(PlanExecutionJob, pending)
    monkeypatch.setattr(settings, 'worker_execution_enabled', False)
    monkeypatch.setattr(settings, 'runner_http_url', '')
    response = client.post(f'/api/v1/test-plans/{row.plan_id}/execute-all', headers=auth_headers,
                           json={'async_mode': True, 'auto_ui': False})
    assert response.status_code == 200 and response.json()['data']['async'] is True
    assert db_session.get(PlanExecutionJob, response.json()['data']['job_id']).status == 'pending'
    sync = client.post(f'/api/v1/test-plans/{row.plan_id}/execute-all', headers=auth_headers,
                       json={'async_mode': False})
    assert sync.status_code == 503
