from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.models.audit import AuditLog
from app.models.environment import Environment
from app.models.test_case import TestCase as _TestCase
from app.models.user import User
from app.services.api_execution_service import (
    _check_prod_protection,
    execute_api_case,
    quick_execute,
)
from app.services.production_operation_guard import (
    ProductionOperation,
    require_allowed_operation,
)


def _user(db_session, username: str = 'audit-user') -> User:
    user = User(username=username, password='x', nickname='Audit Nickname', status=1)
    db_session.add(user)
    db_session.commit()
    return user


def _production_environment(db_session, project_id: int = 1) -> Environment:
    environment = Environment(
        project_id=project_id,
        name='Production audit target',
        env_type='prod',
        is_production=True,
        base_url='https://prod.example.invalid',
    )
    db_session.add(environment)
    db_session.commit()
    return environment


def _api_case(db_session, *, depends_on_ids: str = '[]' ) -> _TestCase:
    case = _TestCase(
        project_id=1,
        title='Audit production case',
        case_type='api',
        api_method='GET',
        api_endpoint='https://prod.example.invalid/items',
        api_assertions=json.dumps([{'type': 'status_code', 'expected': 200}]),
        depends_on_ids=depends_on_ids,
    )
    db_session.add(case)
    db_session.commit()
    return case


def test_production_operation_guard_audits_actor(db_session):
    user = _user(db_session, username='guard-actor')
    environment = _production_environment(db_session)

    require_allowed_operation(
        db_session,
        ProductionOperation(
            action='Trigger production regression',
            project_id=1,
            environment_id=environment.id,
            permission='uitest:trigger_prod',
            confirmed=True,
        ),
        {'uitest:trigger_prod'},
        user_id=user.id,
    )

    audit = db_session.query(AuditLog).one()
    assert audit.action == 'production_operation:allowed'
    assert audit.user_id == user.id
    assert audit.username == 'guard-actor'


def test_check_prod_protection_audits_actor(db_session):
    user = _user(db_session, username='engine-actor')
    environment = _production_environment(db_session)

    allowed, message = _check_prod_protection(
        db_session,
        'GET',
        environment.id,
        actor_user_id=user.id,
    )

    assert allowed is True
    assert message == ''
    audit = db_session.query(AuditLog).one()
    assert audit.action == 'apitest:execute_prod'
    assert audit.user_id == user.id
    assert audit.username == 'engine-actor'


def test_quick_execute_propagates_actor_to_core(db_session):
    user = _user(db_session)
    environment = _production_environment(db_session)

    with patch(
        'app.services.api_execution_service._do_execute',
        return_value={'status': 'ok'},
    ) as execute, patch('app.services.notify_service.queue_notification'):
        quick_execute(
            db_session,
            {'method': 'GET', 'url': '/items'},
            assertions=[{"type": "status_code", "expected": 200}],
            project_id=1,
            environment_id=environment.id,
            actor_user_id=user.id,
        )

    assert execute.call_args.kwargs['actor_user_id'] == user.id


def test_execute_api_case_propagates_actor_to_core(db_session):
    user = _user(db_session)
    environment = _production_environment(db_session)
    case = _api_case(db_session)

    with patch(
        'app.services.api_execution_service._do_execute',
        return_value={'status': 'ok'},
    ) as execute:
        execute_api_case(
            db_session,
            case.id,
            project_id=1,
            environment_id=environment.id,
            actor_user_id=user.id,
        )

    assert execute.call_args.kwargs['actor_user_id'] == user.id


def test_execute_api_case_propagates_actor_to_dependencies(db_session):
    user = _user(db_session)
    environment = _production_environment(db_session)
    case = _api_case(db_session, depends_on_ids='[99]')

    with patch(
        'app.services.api_execution_service._resolve_dependencies',
        return_value={},
    ) as resolve, patch(
        'app.services.api_execution_service._do_execute',
        return_value={'status': 'ok'},
    ):
        execute_api_case(
            db_session,
            case.id,
            project_id=1,
            environment_id=environment.id,
            actor_user_id=user.id,
        )

    assert resolve.call_args.kwargs['actor_user_id'] == user.id


def test_quick_execute_propagates_actor_to_dataset(db_session):
    user = _user(db_session)
    environment = _production_environment(db_session)

    with patch(
        'app.services.api_execution_service._execute_with_dataset',
        return_value={'status': 'ok'},
    ) as execute:
        quick_execute(
            db_session,
            {'method': 'GET', 'url': '/items'},
            assertions=[{"type": "status_code", "expected": 200}],
            project_id=1,
            environment_id=environment.id,
            dataset_id=7,
            actor_user_id=user.id,
        )

    assert execute.call_args.kwargs['actor_user_id'] == user.id


def test_audit_failure_blocks_production_execution(db_session):
    environment = _production_environment(db_session)

    with patch(
        'app.services.audit_service.write_audit',
        side_effect=RuntimeError('audit unavailable'),
    ) as audit:
        try:
            result = quick_execute(
                db_session,
                {'method': 'GET', 'url': '/items'},
                assertions=[{"type": "status_code", "expected": 200}],
                project_id=1,
                environment_id=environment.id,
                actor_user_id=42,
            )
        except RuntimeError:
            result = None
        assert audit.called, f'audit not called; result={result!r}'
        if result is not None:
            raise AssertionError(f'production execution did not fail closed: {result!r}')


def test_api_task_worker_uses_creator_as_actor(db_session, monkeypatch):
    from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem
    from app.services import api_task_worker

    user = _user(db_session, username='worker-creator')
    user_id = user.id
    environment = _production_environment(db_session)
    case = _api_case(db_session)
    task = ApiExecutionTask(
        project_id=1,
        task_id='API-B233',
        status='running',
        creator_id=user.id,
        environment_id=environment.id,
        confirm_prod=True,
        total=1,
    )
    db_session.add(task)
    db_session.commit()
    db_session.add(ApiExecutionTaskItem(task_id=task.id, case_id=case.id, status='pending'))
    db_session.commit()

    monkeypatch.setattr(api_task_worker, 'SessionLocal', lambda: db_session)
    with patch(
        'app.services.api_execution_service.execute_api_case',
        return_value={'all_pass': True, 'duration_ms': 1},
    ) as execute, patch('app.services.notify_service.queue_notification'):
        api_task_worker.execute_task(task.id, 1, 'worker-test')

    assert execute.call_args.kwargs['actor_user_id'] == user_id
