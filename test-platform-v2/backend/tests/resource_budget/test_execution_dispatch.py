from unittest.mock import Mock, patch

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient
import httpx
import pytest

from app.core.config import settings
from app.core.execution_dispatch import ExecutionDispatch, RUNNER_ENDPOINTS


def _api(transport):
    app = FastAPI()

    @app.api_route('/heavy/{item}', methods=['GET', 'POST'])
    def local(item: str):
        return {'owner': 'local'}

    factory = lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs)
    app.routes[-1].app = ExecutionDispatch(app.routes[-1].app, client_factory=factory)
    return app


def test_forward_preserves_auth_body_query_status_and_duplicate_cookies():
    runner = FastAPI()

    @runner.post('/heavy/{item}')
    async def heavy(item: str, request: Request, authorization: str = Header('')):
        if authorization != 'Bearer allowed':
            raise HTTPException(403, 'denied')
        response = JSONResponse({'item': item, 'body': await request.json(),
                                 'query': request.url.query, 'cookie': request.cookies.get('session')},
                                status_code=201)
        response.set_cookie('one', '1')
        response.set_cookie('two', '2')
        return response

    with patch.object(settings, 'worker_execution_enabled', False), \
            patch.object(settings, 'runner_http_url', 'http://runner:8000'), \
            TestClient(_api(httpx.ASGITransport(app=runner))) as client:
        denied = client.post('/heavy/7', json={'value': 'not-authorized'})
        assert denied.status_code == 403
        response = client.post('/heavy/7?a=1&a=2', json={'value': 'body'},
                               headers={'Authorization': 'Bearer allowed', 'Cookie': 'session=retained'})
    assert response.status_code == 201
    assert response.json() == {'item': '7', 'body': {'value': 'body'}, 'query': 'a=1&a=2', 'cookie': 'retained'}
    assert len(response.headers.get_list('set-cookie')) == 2


def test_runner_failure_is_retryable_and_never_executes_local():
    calls = []

    def failed(request):
        calls.append(request.method)
        raise httpx.ConnectError('unavailable', request=request)

    with patch.object(settings, 'worker_execution_enabled', False), \
            patch.object(settings, 'runner_http_url', 'http://runner:8000'), \
            TestClient(_api(httpx.MockTransport(failed))) as client:
        response = client.post('/heavy/1', json={'mutation': True})
    assert response.status_code == 503
    assert response.headers['retry-after'] == '5'
    assert calls == ['POST']


def test_combined_role_stays_local_and_missing_runner_fails_closed():
    transport = httpx.MockTransport(Mock(side_effect=AssertionError('network forbidden')))
    with TestClient(_api(transport)) as client:
        with patch.object(settings, 'worker_execution_enabled', True):
            assert client.get('/heavy/1').json() == {'owner': 'local'}
        with patch.object(settings, 'worker_execution_enabled', False), \
                patch.object(settings, 'runner_http_url', ''):
            assert client.get('/heavy/1').status_code == 503


def test_stream_and_hop_headers():
    runner = FastAPI()

    @runner.get('/heavy/{item}')
    async def stream(item: str):
        async def chunks():
            yield b'data: first\n\n'
            yield b'data: second\n\n'
        return StreamingResponse(chunks(), media_type='text/event-stream',
                                 headers={'Connection': 'x-hop', 'x-hop': 'remove'})

    with patch.object(settings, 'worker_execution_enabled', False), \
            patch.object(settings, 'runner_http_url', 'http://runner:8000'), \
            TestClient(_api(httpx.ASGITransport(app=runner))) as client:
        response = client.get('/heavy/1')
    assert response.content == b'data: first\n\ndata: second\n\n'
    assert 'x-hop' not in response.headers
    assert response.headers['content-type'].startswith('text/event-stream')


def test_actual_registry_keeps_durable_submissions_local():
    import importlib
    from app.main import app
    from fastapi.routing import APIRoute

    modules = [importlib.import_module(name) for name in (*RUNNER_ENDPOINTS, 'app.api.v1.requirement_ai')]
    owners = {(route.endpoint.__module__, route.endpoint.__name__): (route.openapi_extra or {}).get('x-execution-owner') == 'runner'
              for module in modules for route in module.router.routes if isinstance(route, APIRoute)}
    for module, names in RUNNER_ENDPOINTS.items():
        assert all(owners[(module, name)] for name in names)
    assert not owners[('app.api.v1.requirement_ai', 'generate_test_cases_async')]
    assert not owners[('app.api.v1.requirement_ai', 'get_ai_task_status')]
    metadata = [op for path in app.openapi()['paths'].values() for op in path.values()
                if isinstance(op, dict) and op.get('x-execution-owner') == 'runner']
    assert len(metadata) == sum(len(names) for names in RUNNER_ENDPOINTS.values())


def test_real_included_route_dispatches_after_fastapi_aggregation(client, monkeypatch):
    observed = []

    def upstream(request):
        observed.append(request.url.path)
        return httpx.Response(202, stream=httpx.ByteStream(b'{"owner":"runner"}'),
                              headers={'content-type': 'application/json'})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(settings, 'worker_execution_enabled', False)
    monkeypatch.setattr(settings, 'runner_http_url', 'http://runner:8000')
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original_client(
        transport=httpx.MockTransport(upstream), **kwargs))
    response = client.post('/api/v1/playground/execute', json={'spec_code': 'test'})
    assert response.status_code == 202
    assert response.json() == {'owner': 'runner'}
    assert observed == ['/api/v1/playground/execute']


@pytest.mark.parametrize('body', [b'{"async_mode":false,"environment_id":17}', b'null', b''])
def test_mixed_plan_sync_body_survives_inspection(client, monkeypatch, body):
    observed = []

    def upstream(request):
        observed.append(request.content)
        return httpx.Response(200, stream=httpx.ByteStream(b'{"code":0}'),
                              headers={'content-type': 'application/json'})

    original = httpx.AsyncClient
    monkeypatch.setattr(settings, 'worker_execution_enabled', False)
    monkeypatch.setattr(settings, 'runner_http_url', 'http://runner:8000')
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(
        transport=httpx.MockTransport(upstream), **kwargs))
    result = client.post('/api/v1/test-plans/1/execute-all', content=body,
                         headers={'content-type': 'application/json'})
    assert result.status_code == 200
    assert observed == [body]
