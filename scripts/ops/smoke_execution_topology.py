"""Rehearse real split/combined transitions in a disposable local Compose project.

Uses the repository's actual Compose files, PostgreSQL and Temporal gateway.
Does not invoke the production SSH executor or use production credentials/data.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / 'test-platform-v2/deploy'
sys.path.insert(0, str(ROOT / 'deploy/release-console'))
from tencent_executor import rollback_runtime_override


def main():
    project = 'capacity-transition-' + uuid.uuid4().hex[:10]
    password = secrets.token_urlsafe(24)
    env = {key: value for key, value in os.environ.items() if key.upper() in {
        'PATH', 'SYSTEMROOT', 'COMSPEC', 'TEMP', 'TMP', 'HOME', 'USERPROFILE',
        'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
        'PROGRAMW6432', 'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_CONFIG'}}
    env.update({
        'POSTGRES_USER': 'cameltv', 'POSTGRES_PASSWORD': password, 'POSTGRES_DB': 'capacity',
        'ENVIRONMENT': 'development', 'SECRET_KEY': secrets.token_urlsafe(48),
        'ADMIN_USERNAME': 'capacity-admin', 'ADMIN_PASSWORD': password,
        'TESTER_PASSWORD': secrets.token_urlsafe(24), 'COOKIE_SECURE': 'false',
        'DATABASE_URL': f'postgresql+psycopg2://cameltv:{password}@postgres:5432/capacity',
        'AI_ENABLED': 'false', 'DSH_ENABLED': 'false', 'RAG_ENABLED': 'false',
        'KNOWLEDGE_INGEST_ENABLED': 'false', 'LANHU_MCP_ENABLED': 'false',
        'TEMPORAL_ENABLED': 'true', 'TEMPORAL_GRPC_ENDPOINT': 'temporal:7233',
        'TEMPORAL_TASK_QUEUE': project, 'AITDE_V3_ENABLED': 'true',
        'FRONTEND_PORT': '127.0.0.1:0', 'API_IMAGE': 'cameltv-tp-api:capacity-local',
        'RUNNER_IMAGE': 'cameltv-tp-runner:capacity-local',
        'API_MEMORY_LIMIT': '384m', 'RUNNER_MEMORY_LIMIT': '1536m',
        'TEMPORAL_WORKER_MEMORY_LIMIT': '512m',
        'AITDE_WORKER_KEY': project, 'WORKER_HEARTBEAT_SECONDS': '5',
    })

    def run(command, timeout=300):
        result = subprocess.run(command, env=env, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout)
        if result.returncode:
            detail = (result.stdout + result.stderr).replace(password, '[redacted]')
            raise RuntimeError(f'{command[:2]} failed: ' + detail[-4000:])
        return result.stdout.strip()

    with tempfile.TemporaryDirectory(prefix=project) as temporary:
        local = Path(temporary)
        override = local / 'local.json'
        rollback_override = local / 'rollback.json'
        is_rollback = False
        override.write_text(json.dumps({'services': {
            'postgres': {'image': 'postgres:16-alpine', 'mem_limit': '256m'},
            'backend': {'image': 'cameltv-tp-backend:release-20260907-0001'},
            'volume-permissions': {'image': 'cameltv-tp-backend:release-20260907-0001'},
            'aitde-worker': {'image': 'cameltv-tp-backend:release-20260907-0001'},
            'frontend': {'image': 'cameltv-tp-frontend:capacity-local'},
            'temporal': {
                'image': 'temporalio/auto-setup:1.25.2', 'mem_limit': '512m',
                'environment': {'DB': 'postgres12', 'DB_PORT': '5432',
                                'POSTGRES_USER': 'cameltv', 'POSTGRES_PWD': password,
                                'POSTGRES_SEEDS': 'postgres', 'TEMPORAL_ADDRESS': 'temporal:7233'},
                'depends_on': {'postgres': {'condition': 'service_healthy'}},
                'healthcheck': {'test': ['CMD-SHELL', 'temporal operator cluster health --address temporal:7233'],
                                'interval': '5s', 'timeout': '5s', 'retries': 30},
            },
        }}), encoding='utf-8')

        def compose(mode, *arguments, timeout=300):
            command = ['docker', 'compose', '-p', project, '--env-file', os.devnull,
                       '-f', str(DEPLOY / 'docker-compose.yml'), '-f', str(override)]
            if mode == 'split':
                command.extend(['-f', str(DEPLOY / 'docker-compose.execution.yml')])
            if is_rollback:
                command.extend(['-f', str(rollback_override)])
            return run([*command, *arguments], timeout=timeout)

        results = []
        plan_id = None
        try:
            for position, mode in enumerate(('split', 'combined', 'split')):
                if position:
                    compose('split', 'stop', '--timeout', '30', 'backend', 'aitde-worker', 'runner')
                is_rollback = position > 0
                rollback_override.write_text(json.dumps(rollback_runtime_override(mode)), encoding='utf-8')
                compose(mode, 'up', '-d', '--no-build', '--force-recreate', '--wait',
                        '--wait-timeout', '180', 'backend', 'frontend', 'temporal')
                address = compose(mode, 'port', 'frontend', '80').splitlines()[0]
                with httpx.Client(base_url=f'http://{address}', timeout=60) as client:
                    assert client.get('/api/v1/open/health').status_code == 200
                    login = client.post('/api/v1/auth/login', json={'username': 'capacity-admin', 'password': password})
                    assert login.status_code == 200 and login.json()['code'] == 0, 'Real topology login failed'
                    token = login.json()['data']['access_token']
                    headers = {'Authorization': f'Bearer {token}', 'X-Project-Id': '1'}
                    machine_token = client.post('/api/v1/tokens', headers=headers,
                                                json={'name': project, 'scopes': ['workers:register']})
                    assert machine_token.status_code == 200 and machine_token.json()['code'] == 0
                    env['AITDE_WORKER_API_TOKEN'] = machine_token.json()['data']['token']
                    compose(mode, 'up', '-d', '--no-build', '--no-deps', '--force-recreate',
                            '--wait', '--wait-timeout', '90', 'aitde-worker')
                    for attempt in range(10):
                        registered = client.get('/api/v2/workers', headers=headers)
                        if registered.status_code == 200 and any(
                            item['worker_key'] == project for item in registered.json()['data']['items']
                        ):
                            break
                        time.sleep(1)
                    else:
                        raise RuntimeError('Real worker heartbeat registration failed')
                    worker_browser = None
                    if mode == 'split':
                        worker_id = compose(mode, 'ps', '-q', 'aitde-worker')
                        probe = '''from app.core.resource_budget import configured_budget
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
with configured_budget().wait('browser', 'temporal-container-smoke', timeout=5):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        try:
            page = browser.new_page()
            page.set_content('<h1>worker browser</h1>')
            assert page.locator('h1').inner_text() == 'worker browser'
            print(json.dumps({k:int((Path('/sys/fs/cgroup')/k).read_text()) for k in ('memory.current','memory.peak')}))
        finally:
            browser.close()
'''
                        worker_browser = json.loads(run(['docker', 'exec', worker_id, 'python', '-c', probe]))
                    if plan_id is None:
                        created = client.post('/api/v1/test-plans', headers=headers, json={'name': project})
                        assert created.status_code == 200 and created.json()['code'] == 0
                        plan_id = created.json()['data']['id']
                    persisted = client.get(f'/api/v1/test-plans/{plan_id}', headers=headers)
                    assert persisted.status_code == 200 and persisted.json()['code'] == 0, 'Plan lost during topology transition'
                    code = ("import {test,expect} from '@playwright/test';"
                            "test('transition',async({page})=>{await page.setContent('<h1>preserved</h1>');"
                            "await expect(page.locator('h1')).toHaveText('preserved');});")
                    browser = client.post('/api/v1/playground/execute', headers=headers,
                                          json={'spec_code': code, 'timeout_ms': 15000})
                    assert browser.status_code == 200 and browser.json()['passed'], 'Browser failed after transition'
                containers = compose('split', 'ps', '-aq').splitlines()
                memory = run(['docker', 'stats', '--no-stream', '--format', '{{.Name}} {{.MemUsage}}', *containers])
                worker_logs = compose(mode, 'logs', '--tail', '40', 'aitde-worker')
                assert 'Traceback' not in worker_logs, 'Temporal worker failed'
                results.append({'mode': mode, 'plan_preserved': True, 'browser_passed': True,
                                'memory': memory, 'worker_browser': worker_browser})
                print(json.dumps({'progress': results[-1]}), flush=True)
            print(json.dumps({'result': 'passed', 'transitions': results,
                              'limits_are_provisional': True}), flush=True)
        except Exception:
            # Capture migration/runtime failures before deleting the disposable
            # resources. Redact any temporary credentials from diagnostic output.
            diagnostic = compose('split', 'logs', '--tail', '35', 'backend', 'runner', 'aitde-worker')
            for value in (password, env['SECRET_KEY'], env.get('AITDE_WORKER_API_TOKEN', '')):
                if value:
                    diagnostic = diagnostic.replace(value, '[redacted]')
            print(diagnostic, flush=True)
            raise
        finally:
            # Only resources owned by this unique disposable Compose project.
            compose('split', 'down', '--volumes', '--remove-orphans', timeout=120)


if __name__ == '__main__':
    main()
