from unittest.mock import patch
import os
import subprocess
import sys

from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core import scheduler
from app.models.test_schedule import TestSchedule as Schedule, TestScheduleRun as ScheduleRun
from app.services import ai_tasks, api_task_worker, ui_runner_queue, schedule_service
from app.services.dsh import dsh_task_service
from app.services.knowledge import agent_queue


def test_api_role_cannot_start_consumers_or_ui_pool():
    with patch.object(settings, 'worker_execution_enabled', False), \
            patch.object(ai_tasks._loop, 'start') as ai, \
            patch.object(api_task_worker._loop, 'start') as api, \
            patch.object(dsh_task_service._loop, 'start') as dsh, \
            patch.object(ui_runner_queue, '_get_executor') as ui, \
            patch.object(agent_queue.threading, 'Thread') as knowledge:
        ai_tasks.ensure_worker_running()
        api_task_worker.ensure_processor_running()
        dsh_task_service.ensure_worker_running()
        ui_runner_queue.ensure_processor_running()
        ui_runner_queue.enqueue_run(1, 2, 3)
        agent_queue.ensure_processor_running()
    for start in (ai, api, dsh, ui, knowledge):
        start.assert_not_called()


def test_api_role_cannot_start_or_mutate_scheduler():
    with patch.object(settings, 'worker_execution_enabled', False), \
            patch.object(scheduler, 'scheduler') as timer:
        scheduler.init_scheduler()
        scheduler.add_schedule_job(1, '* * * * *')
        scheduler.remove_schedule_job(1)
    timer.start.assert_not_called()
    timer.add_job.assert_not_called()
    timer.remove_job.assert_not_called()


def test_manual_trigger_survives_api_to_worker_handoff(db_session):
    row = Schedule(project_id=1, name='durable trigger', enabled=False,
                   cron_expression='0 6 * * *', job_type='plan')
    db_session.add(row)
    db_session.commit()
    with patch.object(settings, 'worker_execution_enabled', False), \
            patch('threading.Thread') as thread:
        submitted = schedule_service.trigger_schedule(db_session, row.id, 1)
    thread.assert_not_called()
    run = db_session.get(ScheduleRun, submitted['run_id'])
    assert run.status == 'running'
    assert run.heartbeat_at is None
    factory = sessionmaker(bind=db_session.get_bind())
    with patch('app.core.db.SessionLocal', factory), \
            patch('app.services.test_plan_service.execute_all_cases', return_value={
                'total': 1, 'passed': 1, 'failed': 0, 'skipped': 0,
            }) as execute, \
            patch('app.services.notify_service.notify_sync'):
        scheduler.poll_pending_schedule_runs()
        scheduler.poll_pending_schedule_runs()
        duplicate = scheduler._execute_schedule(row.id, run.id)
    assert execute.call_count == 1
    assert duplicate['reason'] == 'already_claimed'
    db_session.refresh(run)
    assert run.status == 'passed'
    assert run.heartbeat_at is not None


def test_disabled_cron_does_not_execute_after_registry_lag(db_session):
    row = Schedule(project_id=1, name='disabled', enabled=False,
                   cron_expression='0 6 * * *', job_type='plan')
    db_session.add(row)
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())
    with patch('app.core.db.SessionLocal', factory), \
            patch('app.services.test_plan_service.execute_all_cases') as execute:
        scheduler._execute_schedule(row.id)
    execute.assert_not_called()


def test_registry_reconciles_cross_process_schedule_edits(db_session):
    from apscheduler.schedulers.background import BackgroundScheduler

    timer = BackgroundScheduler()
    row = Schedule(project_id=1, name='cron', enabled=True, cron_expression='0 6 * * *')
    db_session.add(row)
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind())
    with patch('app.core.db.SessionLocal', factory), patch.object(scheduler, 'scheduler', timer):
        timer.start(paused=True)
        try:
            scheduler.refresh_schedule_jobs()
            first = str(timer.get_job(f'schedule_{row.id}').trigger)
            row.cron_expression = '0 7 * * *'
            db_session.commit()
            scheduler.refresh_schedule_jobs()
            assert str(timer.get_job(f'schedule_{row.id}').trigger) != first
            row.enabled = False
            db_session.commit()
            scheduler.refresh_schedule_jobs()
            assert timer.get_job(f'schedule_{row.id}') is None
        finally:
            timer.shutdown()


def test_manual_trigger_consumed_once_by_fresh_processes(tmp_path):
    import app.models  # noqa: F401
    from sqlalchemy import create_engine
    from app.core.db import Base

    url = 'sqlite:///' + (tmp_path / 'handoff.db').as_posix()
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        row = Schedule(project_id=1, enabled=False, cron_expression='0 6 * * *', job_type='plan')
        db.add(row)
        db.commit()
        with patch.object(settings, 'worker_execution_enabled', False):
            submitted = schedule_service.trigger_schedule(db, row.id, 1)
    marker = tmp_path / 'executions.txt'
    source = '''
import sys, threading
from pathlib import Path
import app.models
from app.worker import run_worker
from app.services import test_plan_service, notify_service
def execute(*args, **kwargs):
    path = Path(sys.argv[1])
    path.write_text((path.read_text() if path.exists() else '') + 'executed\\n')
    return dict(total=1, passed=1, failed=0, skipped=0)
test_plan_service.execute_all_cases = execute
notify_service.notify_sync = lambda *a, **kw: None
stop = threading.Event()
timer = threading.Timer(4, stop.set)
timer.start()
run_worker(stop, Path(sys.argv[1]).with_suffix('.heartbeat'))
timer.join()
'''
    env = {**os.environ, 'DATABASE_URL': url, 'WORKER_EXECUTION_ENABLED': 'true'}
    for _ in range(2):
        result = subprocess.run([sys.executable, '-c', source, str(marker)],
                                env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
    assert marker.read_text().splitlines() == ['executed']
    with factory() as db:
        assert db.get(ScheduleRun, submitted['run_id']).status == 'passed'
    engine.dispose()
