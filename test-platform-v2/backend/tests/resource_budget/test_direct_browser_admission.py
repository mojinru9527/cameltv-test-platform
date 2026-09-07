from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.resource_budget import configured_budget
from app.schemas.playground import ExecuteRequest
from app.services import playground_service, test_plan_service


@pytest.fixture
def budget(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'worker_execution_enabled', True)
    monkeypatch.setattr(settings, 'heavy_task_budget_enabled', True)
    monkeypatch.setattr(settings, 'heavy_task_budget_dir', str(tmp_path / 'budget'))
    monkeypatch.setattr(settings, 'heavy_task_budget_capacity', 1)
    return configured_budget()


def test_busy_direct_paths_do_not_compile_or_launch(budget, monkeypatch):
    launch = Mock(side_effect=AssertionError('must not launch'))
    monkeypatch.setattr(playground_service, '_execute_spec_owned', launch)
    monkeypatch.setattr(test_plan_service, '_execute_ui_case_owned', launch)
    with budget.try_acquire('ui', 'existing'):
        with pytest.raises(HTTPException) as caught:
            playground_service.execute_spec(ExecuteRequest(spec_code='test'))
        assert caught.value.status_code == 429
        assert caught.value.headers['Retry-After'] == '5'
        result = test_plan_service._execute_ui_case_sync(None, SimpleNamespace(id=1), 1)
        assert result['blocked'] is True
        assert result['ok'] is False
    launch.assert_not_called()


@pytest.mark.parametrize('target', ['playground', 'plan'])
def test_direct_owner_keeps_lease_until_exit_and_releases_on_error(budget, monkeypatch, target):
    def owned(*args, **kwargs):
        assert budget.try_acquire('probe', 'during') is None
        raise RuntimeError('execution failed')

    if target == 'playground':
        monkeypatch.setattr(playground_service, '_execute_spec_owned', owned)
        invoke = lambda: playground_service.execute_spec(ExecuteRequest(spec_code='test'))
    else:
        monkeypatch.setattr(test_plan_service, '_execute_ui_case_owned', owned)
        invoke = lambda: test_plan_service._execute_ui_case_sync(None, SimpleNamespace(id=1), 1)
    with pytest.raises(RuntimeError, match='execution failed'):
        invoke()
    lease = budget.try_acquire('probe', 'after')
    assert lease is not None
    lease.release()


def test_api_role_never_runs_direct_browser(monkeypatch):
    monkeypatch.setattr(settings, 'worker_execution_enabled', False)
    with pytest.raises(HTTPException) as caught:
        playground_service.execute_spec(ExecuteRequest(spec_code='test'))
    assert caught.value.status_code == 503
    assert test_plan_service._execute_ui_case_sync(None, SimpleNamespace(id=1), 1)['blocked']


@pytest.mark.parametrize('case_type', ['ui', 'manual'])
def test_busy_plan_records_blocked_without_false_failure(budget, db_session, case_type):
    from app.models.test_case import TestCase as Case
    from app.models.test_plan import TestExecution as Execution, TestPlan as Plan, TestPlanCase as PlanCase
    from sqlalchemy import select

    plan = Plan(project_id=1, name='capacity')
    case = Case(project_id=1, title='capacity', case_type=case_type, priority='P0',
                steps='[{"step": 1, "desc": "open page", "expected": "visible"}]')
    db_session.add_all([plan, case])
    db_session.flush()
    plan_case = PlanCase(plan_id=plan.id, case_id=case.id)
    db_session.add(plan_case)
    db_session.commit()
    with budget.try_acquire('ui', 'existing'):
        result = test_plan_service.execute_all_cases(db_session, plan.id, project_id=1, auto_ui=True)
    assert result['failed'] == 0
    assert result['executed'] == 0
    assert result['details'][0]['status'] == 'blocked'
    assert plan_case.last_status == 'blocked'
    assert db_session.scalar(select(Execution)).status == 'blocked'


def test_missing_npx_returns_error_without_cleanup_exception(monkeypatch):
    monkeypatch.setattr(settings, 'worker_execution_enabled', True)
    monkeypatch.setattr(settings, 'heavy_task_budget_enabled', False)
    monkeypatch.setattr(test_plan_service, '_compile_ui_case', lambda *args: ('// valid spec', 'rules'))
    monkeypatch.setattr(test_plan_service.shutil, 'which', lambda *args: None)
    result = test_plan_service._execute_ui_case_sync(None, SimpleNamespace(id=987654, case_id='capacity-check'), 1)
    assert result['ok'] is False
    assert 'npx/playwright' in result['error']
