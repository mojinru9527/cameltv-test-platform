"""Disposable local API/runner HTTP smoke; does not deploy or read production data."""
import json
import secrets
import subprocess
import time
import uuid
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[2]


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f'Docker {args[0]} failed (exit {result.returncode})')
    return result.stdout.strip()


def wait_healthy(name):
    for _ in range(60):
        result = subprocess.run(
            ['docker', 'exec', name, 'python', '-c',
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(f'{name} did not become healthy')


def main():
    prefix = f'capacity-smoke-{uuid.uuid4().hex[:10]}'
    network, volume = prefix, f'{prefix}-data'
    containers = []
    password = secrets.token_urlsafe(24)
    env = {
        'ENVIRONMENT': 'development', 'SECRET_KEY': secrets.token_urlsafe(48),
        'ADMIN_USERNAME': 'capacity-admin', 'ADMIN_PASSWORD': password,
        'TESTER_PASSWORD': secrets.token_urlsafe(24), 'COOKIE_SECURE': 'false',
        'DATABASE_URL': 'sqlite:////app/storage/smoke.db',
        'AI_ENABLED': 'false', 'DSH_ENABLED': 'false', 'RAG_ENABLED': 'false',
        'KNOWLEDGE_INGEST_ENABLED': 'false', 'LANHU_MCP_ENABLED': 'false',
        'HEAVY_TASK_BUDGET_ENABLED': 'true', 'HEAVY_TASK_BUDGET_CAPACITY': '1',
        'HEAVY_TASK_BUDGET_DIR': '/app/storage/resource-budget',
    }
    docker('network', 'create', network)
    try:
        docker('volume', 'create', volume)
        docker('run', '--rm', '--user', '0:0', '-v', f'{volume}:/app/storage',
               '--entrypoint', 'chown', 'cameltv-tp-api:capacity-local', '-R', '10001:10001', '/app/storage')
        for role, limit in (('runner', '1536m'), ('api', '512m')):
            name = f'{prefix}-{role}'
            containers.append(name)
            config = {**env, 'WORKER_EXECUTION_ENABLED': str(role == 'runner').lower(),
                      'AUTO_CREATE_TABLES': str(role == 'runner').lower(),
                      'RUNNER_HTTP_URL': 'http://runner:8000' if role == 'api' else ''}
            args = ['run', '-d', '--name', name, '--network', network, '--network-alias', role,
                    '--init', '--memory', limit, '--pids-limit', '256',
                    '-v', f'{volume}:/app/storage',
                    '--mount', f'type=bind,source={ROOT / "test-platform-v2/backend/app"},target=/app/app,readonly']
            if role == 'api':
                args.extend(['-p', '127.0.0.1::8000'])
            for key, value in config.items():
                args.extend(['-e', f'{key}={value}'])
            args.extend(['--entrypoint', 'uvicorn', f'cameltv-tp-{role}:capacity-local',
                         'app.main:app', '--host', '0.0.0.0', '--port', '8000'])
            docker(*args)
            wait_healthy(name)

        address = docker('port', containers[1], '8000/tcp').splitlines()[0]
        with httpx.Client(base_url=f'http://{address}', timeout=60) as client:
            denied = client.post('/api/v1/playground/execute', json={'spec_code': '// denied'})
            assert denied.status_code in (401, 403), 'Runner must enforce authentication'
            login = client.post('/api/v1/auth/login', json={'username': 'capacity-admin', 'password': password})
            assert login.status_code == 200 and login.json().get('code') == 0, 'Login failed'
            token = login.json()['data']['access_token']
            # The fresh seed creates project 1; project context is mandatory even
            # for administrators and must survive forwarding to the runner.
            headers = {'Authorization': f'Bearer {token}', 'X-Project-Id': '1'}
            code = (
                "import {test,expect} from '@playwright/test';"
                "test('capacity smoke',async({page})=>{"
                "await page.setContent('<h1>capacity smoke</h1>');"
                "await expect(page.locator('h1')).toHaveText('capacity smoke');});"
            )
            executed = client.post('/api/v1/playground/execute', headers=headers,
                                   json={'spec_code': code, 'timeout_ms': 15000})
            if executed.status_code != 200 or not executed.json().get('passed'):
                detail = executed.json()
                raise RuntimeError(f'Cross-container browser execution failed: HTTP {executed.status_code}; '
                                   f'{detail.get("stderr", detail.get("detail", detail.get("msg", detail.get("message", "no detail"))))}')
            created = client.post('/api/v1/test-plans', headers=headers, json={'name': 'capacity async plan'})
            assert created.status_code == 200 and created.json().get('code') == 0, 'Plan creation failed'
            plan_id = created.json()['data']['id']
            stats = docker('stats', '--no-stream', '--format', '{{.Name}} {{.MemUsage}}', *containers)
            docker('stop', '--time', '10', containers[0])
            unavailable = client.post('/api/v1/playground/execute', headers=headers,
                                      json={'spec_code': code, 'timeout_ms': 15000})
            assert unavailable.status_code == 503, 'Missing runner must fail closed'
            assert unavailable.headers.get('retry-after') == '5'
            assert client.get('/health').status_code == 200, 'API must remain responsive'
            queued = client.post(f'/api/v1/test-plans/{plan_id}/execute-all', headers=headers,
                                 json={'async_mode': True, 'auto_ui': False})
            assert queued.status_code == 200 and queued.json()['data']['job_id'], 'Async submission must persist during outage'
            job_id = queued.json()['data']['job_id']
            jobs_url = f'/api/v1/test-plans/{plan_id}/execution-jobs'
            assert client.get(jobs_url, headers=headers).json()['data'][0]['status'] == 'pending'
            docker('start', containers[0])
            wait_healthy(containers[0])
            for _ in range(30):
                jobs = client.get(jobs_url, headers=headers).json()['data']
                job = next(item for item in jobs if item['id'] == job_id)
                if job['status'] == 'completed':
                    break
                time.sleep(1)
            else:
                raise RuntimeError('Pending plan did not complete after runner restart')
        print(json.dumps({'result': 'passed', 'checks': ['auth', 'login', 'real-browser-forward',
                         'runner-outage-503', 'api-stays-responsive', 'async-accepted-during-outage',
                         'async-completed-after-restart'], 'post_run_memory': stats}))
    finally:
        # Only the fresh resources named by this invocation are removed.
        for name in reversed(containers):
            docker('rm', '-f', name)
        docker('volume', 'rm', volume)
        docker('network', 'rm', network)


if __name__ == '__main__':
    main()
