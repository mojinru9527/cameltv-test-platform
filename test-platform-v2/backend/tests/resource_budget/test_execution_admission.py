from unittest.mock import Mock, patch

import pytest

from app.core.resource_budget import FileBudget
from app.modules.aitde.browser import driver
from app.services.knowledge import embedding_service as embedding
from app.services.lanhu_evidence import job_runner


def test_direct_lanhu_call_is_deferred_before_any_work(tmp_path):
    budget = FileBudget(tmp_path, 1)
    with budget.wait('ui', '1', timeout=0), \
            patch('app.core.resource_budget.configured_budget', return_value=budget), \
            patch.object(job_runner, '_run_admitted_job') as run:
        job_runner.run_job_in_new_session(1, 2)
    run.assert_not_called()


def test_lanhu_handoff_does_not_reacquire_and_caller_retains_ownership(tmp_path):
    budget = FileBudget(tmp_path, 1)
    with budget.wait('lanhu', '1', timeout=0) as lease, \
            patch('app.core.resource_budget.configured_budget', return_value=budget), \
            patch.object(job_runner, '_run_admitted_job') as run:
        job_runner.run_job_in_new_session(1, 2, resource_lease=lease)
        run.assert_called_once_with(1, 2, None)
        assert budget.try_acquire('ui', '2') is None
    with budget.wait('ui', '2', timeout=0):
        pass


def test_busy_embedding_does_not_load_model_or_run_inference(tmp_path):
    budget = FileBudget(tmp_path, 1)
    service = embedding.EmbeddingService()
    with budget.wait('ui', '1', timeout=0), \
            patch.object(embedding, 'configured_budget', return_value=budget), \
            patch.object(service, '_ensure_model') as load:
        assert service.available() is False
        assert service.embed(['text']) is None
    load.assert_not_called()
    assert service._unavailable is False


def test_embedding_error_releases_admission(tmp_path):
    budget = FileBudget(tmp_path, 1)
    service = embedding.EmbeddingService()
    service._model = Mock()
    service._model.embed.side_effect = RuntimeError('inference failed')
    with patch.object(embedding, 'configured_budget', return_value=budget):
        assert service.embed(['text']) is None
    with budget.wait('ui', '1', timeout=0):
        pass


def test_browser_busy_starts_no_runtime(tmp_path):
    budget = FileBudget(tmp_path, 1)
    adapter = driver.PlaywrightPageAdapter()
    with budget.wait('lanhu', '1', timeout=0), \
            patch.object(driver, 'configured_budget', return_value=budget), \
            patch.object(adapter, '_open_admitted') as start:
        with pytest.raises(driver.BrowserRuntimeError, match='capacity'):
            adapter.open()
    start.assert_not_called()


@pytest.mark.parametrize('failure', ['startup', 'close'])
def test_browser_errors_release_and_close_is_idempotent(tmp_path, failure):
    budget = FileBudget(tmp_path, 1)
    adapter = driver.PlaywrightPageAdapter()
    with patch.object(driver, 'configured_budget', return_value=budget), \
            patch.object(adapter, '_open_admitted') as start:
        if failure == 'startup':
            start.side_effect = RuntimeError('startup failed')
            with pytest.raises(RuntimeError, match='startup'):
                adapter.open()
        else:
            adapter.open()
            adapter._browser = Mock()
            adapter._browser.close.side_effect = RuntimeError('close failed')
            adapter._pw = Mock()
            pw = adapter._pw
            with pytest.raises(RuntimeError, match='close'):
                adapter.close()
            pw.stop.assert_called_once()
    adapter.close()
    with budget.wait('ui', 'next', timeout=0):
        pass


def test_api_role_never_loads_embedding_model_or_runs_local_binaries():
    from app.core.config import settings
    from app.services import playwright_executor
    from app.services.dsh import dsh_runner

    service = embedding.EmbeddingService()
    with patch.object(settings, 'worker_execution_enabled', False), \
            patch.object(settings, 'runner_http_url', 'http://runner:8000'), \
            patch.object(service, '_ensure_model') as load, \
            patch.object(playwright_executor, '_resolve_cmd') as lookup:
        assert service.available() is False
        assert service.embed(['text']) is None
        assert playwright_executor._check_playwright_installed()[0] is True
        assert dsh_runner.run_dsh_task('task').exit_code == 75
    load.assert_not_called()
    lookup.assert_not_called()
