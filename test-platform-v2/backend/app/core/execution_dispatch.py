"""Forward explicitly owned HTTP endpoints to the internal execution service.

The runner serves the same routes and performs their existing authentication,
project scoping and validation. Queued submissions are not in this registry.
"""
from __future__ import annotations

import httpx
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from app.core.config import settings


RUNNER_ENDPOINTS = {
    'app.api.v1.playground': {'batch_compile_endpoint', 'batch_run_endpoint', 'compile_endpoint', 'execute_endpoint'},
    'app.api.v1.ui_test': {'create_capture', 'get_capture', 'runner_health', 'create_jobs_from_cases'},
    'app.api.v1.dsh_tasks': {'dsh_health'},
    'app.api.v1.test_plan_execution': {'execute_all_cases'},
    'app.api.v1.knowledge_core': {'search_knowledge', 'search_health', 'reembed'},
    'app.api.v1.open_knowledge': {'open_search_knowledge'},
    'app.api.v1.requirement_ai_generate': {'generate_test_cases'},
}

_HOP_HEADERS = {b'connection', b'keep-alive', b'proxy-authenticate', b'proxy-authorization',
                b'te', b'trailer', b'transfer-encoding', b'upgrade'}


def _forward_headers(raw_headers):
    blocked = set(_HOP_HEADERS)
    for name, value in raw_headers:
        if name.lower() == b'connection':
            blocked.update(part.strip().lower() for part in value.split(b','))
    return [(name, value) for name, value in raw_headers if name.lower() not in blocked]


class ExecutionDispatch:
    def __init__(self, local_app, *, client_factory=None):
        self.local_app = local_app
        self.client_factory = client_factory

    async def __call__(self, scope, receive, send):
        if settings.worker_execution_enabled:
            await self.local_app(scope, receive, send)
            return
        if not settings.runner_http_url:
            await self._unavailable(scope, receive, send)
            return
        try:
            base = httpx.URL(settings.runner_http_url)
        except httpx.InvalidURL:
            await self._unavailable(scope, receive, send)
            return
        if (base.scheme not in ('http', 'https') or not base.host or base.userinfo
                or base.path not in ('', '/') or base.query or base.fragment):
            await self._unavailable(scope, receive, send)
            return
        raw_path = scope.get('raw_path') or scope['path'].encode('utf-8')
        query = scope.get('query_string', b'')
        url = base.copy_with(raw_path=raw_path + (b'?' + query if query else b''))
        request = Request(scope, receive)
        # Do not retry mutations: an upstream may have committed before disconnect.
        timeout = httpx.Timeout(connect=5, read=3600, write=60, pool=5)
        response_started = False
        try:
            factory = self.client_factory or httpx.AsyncClient
            async with factory(timeout=timeout, follow_redirects=False) as client:
                async with client.stream(scope['method'], url,
                                         headers=_forward_headers(scope['headers']),
                                         content=request.stream()) as upstream:
                    response = StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code)
                    response.raw_headers = _forward_headers(upstream.headers.raw)
                    response_started = True
                    await response(scope, receive, send)
        except httpx.HTTPError:
            if response_started:
                raise
            await self._unavailable(scope, receive, send)

    @staticmethod
    async def _unavailable(scope, receive, send):
        response = JSONResponse({'detail': 'Execution service unavailable; retry later'},
                                status_code=503, headers={'Retry-After': '5'})
        await response(scope, receive, send)


class ExecutionRoute(APIRoute):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        names = RUNNER_ENDPOINTS.get(self.endpoint.__module__, set())
        if self.endpoint.__name__ in names:
            self.openapi_extra = {**(self.openapi_extra or {}), 'x-execution-owner': 'runner'}
            if self._mixed_plan_route():
                self.openapi_extra['x-async-submission-owner'] = 'api'

    def _mixed_plan_route(self):
        return (self.endpoint.__module__ == 'app.api.v1.test_plan_execution'
                and self.endpoint.__name__ == 'execute_all_cases')

    def get_route_handler(self):
        local_handler = super().get_route_handler()
        names = RUNNER_ENDPOINTS.get(self.endpoint.__module__, set())
        if self.endpoint.__name__ not in names:
            return local_handler

        async def handler(request: Request):
            if settings.worker_execution_enabled:
                return await local_handler(request)
            if self._mixed_plan_route():
                from app.api.v1.test_plan_execution import ExecuteAllBody
                body = await request.body()
                try:
                    data = ExecuteAllBody.model_validate_json(body) if body and body.strip() != b'null' else ExecuteAllBody()
                except ValidationError:
                    # Preserve the framework's existing validation response.
                    return await local_handler(request)
                if data.async_mode:
                    return await local_handler(request)
                return _ForwardedResponse(body=body)
            return _ForwardedResponse()

        return handler


class _ForwardedResponse(Response):
    def __init__(self, *, body=None):
        super().__init__()
        self._buffered_body = body

    async def __call__(self, scope, receive, send):
        if self._buffered_body is None:
            await ExecutionDispatch(None)(scope, receive, send)
            return
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {'type': 'http.request', 'body': self._buffered_body, 'more_body': False}
            return await receive()

        await ExecutionDispatch(None)(scope, replay, send)
