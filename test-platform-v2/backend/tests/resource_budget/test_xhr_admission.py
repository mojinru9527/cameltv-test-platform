from unittest.mock import Mock, patch

import pytest

from app.core.resource_budget import FileBudget
from app.services import xhr_capture_service as capture


def test_busy_capture_does_not_create_task_or_thread(tmp_path):
    budget = FileBudget(tmp_path, 1)
    before = set(capture._TASKS)
    with budget.wait('ui', 'active', timeout=0), \
            patch.object(capture, 'configured_budget', return_value=budget), \
            patch.object(capture.threading, 'Thread') as thread:
        with pytest.raises(capture.CaptureCapacityUnavailable):
            capture.create_capture_task(pages=['/'], project_id=1)
    assert set(capture._TASKS) == before
    thread.assert_not_called()


def test_thread_start_failure_releases_capacity_and_record(tmp_path):
    budget = FileBudget(tmp_path, 1)
    lease = budget.wait('xhr', 'reserved', timeout=0)
    before = set(capture._TASKS)
    with patch.object(capture, 'configured_budget', return_value=Mock(try_acquire=Mock(return_value=lease))), \
            patch.object(capture.threading, 'Thread') as thread:
        thread.return_value.start.side_effect = RuntimeError('thread unavailable')
        with pytest.raises(RuntimeError):
            capture.create_capture_task(pages=['/'], project_id=1)
    assert set(capture._TASKS) == before
    with budget.wait('ui', 'next', timeout=0):
        pass


def test_busy_capture_api_returns_retryable_response(client, auth_headers):
    client.headers.update(auth_headers)
    with patch.object(capture, 'create_capture_task', side_effect=capture.CaptureCapacityUnavailable):
        response = client.post('/api/v1/ui-tests/capture', json={'pages': ['/']})
    assert response.status_code == 429
    assert response.headers['retry-after'] == '5'
    response_schema = client.app.openapi()['paths']['/api/v1/ui-tests/capture']['post']['responses']['429']
    assert 'Retry-After' in response_schema['headers']
