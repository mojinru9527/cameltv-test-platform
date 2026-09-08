from unittest.mock import Mock, patch
import threading

import pytest

from app.core.resource_budget import FileBudget
from app.services.dsh import dsh_runner as runner
from app.services.dsh import dsh_task_service as worker


def test_parent_can_complete_browser_child_while_orchestration_is_full(tmp_path):
    orchestration = FileBudget(tmp_path / 'orchestration', 1)
    execution = FileBudget(tmp_path, 1)

    def run_child(*args, **kwargs):
        assert orchestration.try_acquire('dsh', 'another-parent') is None
        with execution.wait('ui', 'child', timeout=0):
            return runner.DshRunResult(final_response='child finished')

    with patch.object(runner, 'configured_budget', return_value=orchestration), \
            patch.object(runner, 'runtime_available', return_value=(True, '')), \
            patch.object(runner.settings, 'dsh_runtime', 'node'), \
            patch.object(runner, '_run_node_cli', side_effect=run_child):
        result = runner.run_dsh_task('parent', session_root=str(tmp_path / 'sessions'))
    assert result.final_response == 'child finished'
    with orchestration.wait('dsh', 'next-parent', timeout=0):
        pass


def test_busy_orchestration_does_not_claim_or_open_database(tmp_path):
    budget = FileBudget(tmp_path, 1)
    with budget.wait('dsh', 'active', timeout=0), \
            patch.object(worker, 'configured_budget', return_value=budget), \
            patch.object(worker, 'SessionLocal') as session, \
            patch.object(worker, 'claim_next_task') as claim:
        worker._poll_once()
    claim.assert_not_called()
    session.assert_not_called()


@pytest.mark.parametrize('failure', ['empty', 'claim', 'submit'])
def test_poll_failure_releases_orchestration(tmp_path, failure):
    budget = FileBudget(tmp_path, 1)
    with patch.object(worker, 'configured_budget', return_value=budget), \
            patch.object(worker, 'SessionLocal', return_value=Mock()), \
            patch.object(worker, 'claim_next_task') as claim, \
            patch.object(worker, '_executor') as pool:
        claim.return_value = None if failure == 'empty' else Mock(id=1)
        if failure == 'claim':
            claim.side_effect = RuntimeError('database unavailable')
        if failure == 'submit':
            pool.submit.side_effect = RuntimeError('executor stopped')
        worker._poll_once()
    with budget.wait('dsh', 'next', timeout=0):
        pass


def test_database_open_failure_releases_transferred_lease(tmp_path):
    budget = FileBudget(tmp_path, 1)
    lease = budget.wait('dsh', '1', timeout=0)
    with patch.object(worker, 'SessionLocal', side_effect=RuntimeError('offline')):
        with pytest.raises(RuntimeError, match='offline'):
            worker._process_claimed(1, lease)
    with budget.wait('dsh', '2', timeout=0):
        pass


def test_configured_classes_share_execution_but_not_parent_lane(tmp_path):
    from app.core.config import settings
    from app.core.resource_budget import configured_budget

    with patch.object(settings, 'heavy_task_budget_enabled', True), \
            patch.object(settings, 'heavy_task_budget_dir', str(tmp_path)):
        with configured_budget('orchestration').wait('dsh', 'parent', timeout=0):
            with configured_budget().wait('ui', 'child', timeout=0):
                assert configured_budget().try_acquire('lanhu', 'other') is None
                assert configured_budget('orchestration').try_acquire('dsh', 'other') is None


def test_team_monitor_return_does_not_release_live_runner(tmp_path):
    budget = FileBudget(tmp_path, 1)
    started = threading.Event()
    finish = threading.Event()
    threads = []

    def runtime(*args, **kwargs):
        started.set()
        assert finish.wait(5)
        return runner.DshRunResult()

    def monitor(db, task, runner):
        thread = threading.Thread(target=runner, args=('team',))
        threads.append(thread)
        thread.start()
        assert started.wait(2)
        # Simulate the existing monitor returning before execution ends.

    db = Mock()
    db.get.return_value = Mock(status='running')
    lease = budget.wait('dsh', 'team', timeout=0)
    try:
        with patch.object(worker, 'SessionLocal', return_value=db), \
                patch.object(worker, 'execute_task', side_effect=monitor), \
                patch.object(runner, 'run_dsh_task', side_effect=runtime):
            worker._process_claimed(1, lease)
            assert budget.try_acquire('dsh', 'next') is None
            finish.set()
            threads[0].join(2)
    finally:
        finish.set()
        for thread in threads:
            thread.join(5)
    with budget.wait('dsh', 'next', timeout=0):
        pass


def test_late_team_dispatch_cannot_start_after_owner_return(tmp_path):
    budget = FileBudget(tmp_path, 1)
    callbacks = []
    db = Mock()
    db.get.return_value = Mock(status='running')
    lease = budget.wait('dsh', 'team', timeout=0)
    with patch.object(worker, 'SessionLocal', return_value=db), \
            patch.object(worker, 'execute_task', side_effect=lambda db, task, runner: callbacks.append(runner)), \
            patch.object(runner, 'run_dsh_task') as runtime:
        worker._process_claimed(1, lease)
        assert callbacks[0]('late').exit_code == 1
        runtime.assert_not_called()
    with budget.wait('dsh', 'next', timeout=0):
        pass
