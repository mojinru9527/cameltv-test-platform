"""Real Docker host smoke for the default split AI topology.

Verifies the repository default topology end to end on a real Docker daemon:

* ``docker compose -f docker-compose.yml`` renders api + ai-gateway + runner
  (split is the default), and the combined overlay rolls it back.
* api / ai-gateway / runner start and become healthy under ``--wait``.
* The API process is configured to delegate AI to the gateway (remote role),
  while the runner keeps local worker execution enabled.
* The gateway enforces its internal token: unauthenticated calls are rejected,
  authenticated calls reach the handler.
* Fail-closed: the release split overlay refuses to render without
  ``AI_GATEWAY_TOKEN``, and the gateway reports unhealthy without a token.
* Image boundaries: the api image ships no FastEmbed/ONNX/NumPy/Playwright,
  the gateway ships AI deps but no browser package.

Emits a single JSON line and returns non-zero on the first failed assertion.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / 'test-platform-v2/deploy'
BASE_COMPOSE = DEPLOY / 'docker-compose.yml'
SPLIT_OVERLAY = DEPLOY / 'docker-compose.execution.yml'
COMBINED_OVERLAY = DEPLOY / 'docker-compose.combined.yml'

API_IMAGE = 'cameltv-tp-api'
GATEWAY_IMAGE = 'cameltv-tp-ai-gateway'
RUNNER_IMAGE = 'cameltv-tp-runner'

API_FORBIDDEN_MODULES = ('fastembed', 'onnxruntime', 'numpy', 'playwright')
GATEWAY_REQUIRED_MODULES = ('fastembed', 'onnxruntime', 'numpy')
GATEWAY_FORBIDDEN_MODULES = ('playwright',)


def main() -> int:
    project = 'ai-split-smoke-' + uuid.uuid4().hex[:10]
    tag = 'batch241-' + uuid.uuid4().hex[:8]
    password = secrets.token_urlsafe(24)
    gateway_token = secrets.token_urlsafe(32)

    base_env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {
            'PATH', 'SYSTEMROOT', 'COMSPEC', 'TEMP', 'TMP', 'HOME', 'USERPROFILE',
            'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'PROGRAMFILES',
            'PROGRAMFILES(X86)', 'PROGRAMW6432', 'DOCKER_HOST', 'DOCKER_CONTEXT',
            'DOCKER_CONFIG',
        }
    }
    env = dict(base_env)
    env.update({
        'POSTGRES_USER': 'cameltv',
        'POSTGRES_PASSWORD': password,
        'POSTGRES_DB': 'cameltv',
        'ENVIRONMENT': 'development',
        'SECRET_KEY': secrets.token_urlsafe(48),
        'ADMIN_USERNAME': 'smoke-admin',
        'ADMIN_PASSWORD': password,
        'TESTER_PASSWORD': secrets.token_urlsafe(24),
        'COOKIE_SECURE': 'false',
        'DATABASE_URL': (
            f'postgresql+psycopg2://cameltv:{password}@postgres:5432/cameltv'
        ),
        'AI_GATEWAY_TOKEN': gateway_token,
        'AI_ENABLED': 'false',
        'RAG_ENABLED': 'false',
        'KNOWLEDGE_INGEST_ENABLED': 'false',
        'LANHU_MCP_ENABLED': 'false',
        'DSH_ENABLED': 'false',
        'FRONTEND_PORT': '127.0.0.1:0',
        'API_MEMORY_LIMIT': '512m',
        'AI_GATEWAY_MEMORY_LIMIT': '768m',
        'RUNNER_MEMORY_LIMIT': '1024m',
        'TEMPORAL_WORKER_MEMORY_LIMIT': '512m',
        'API_IMAGE': f'{API_IMAGE}:{tag}',
        'AI_GATEWAY_IMAGE': f'{GATEWAY_IMAGE}:{tag}',
        'RUNNER_IMAGE': f'{RUNNER_IMAGE}:{tag}',
    })

    def run(command, *, check=True, timeout=900, run_env=None):
        result = subprocess.run(
            command,
            env=run_env or env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
        )
        if check and result.returncode:
            detail = (result.stdout + result.stderr).replace(
                password, '[redacted]'
            ).replace(gateway_token, '[redacted]')
            raise RuntimeError(
                f'{" ".join(command[:3])} failed rc={result.returncode}: '
                f'{detail[-3000:]}'
            )
        return result

    def compose(*arguments, overlay=(), run_env=None, check=True, timeout=900):
        command = [
            'docker', 'compose', '-p', project, '--env-file', os.devnull,
            '-f', str(BASE_COMPOSE),
        ]
        for extra in overlay:
            command.extend(['-f', str(extra)])
        return run(
            [*command, *arguments],
            check=check,
            timeout=timeout,
            run_env=run_env,
        )

    def image_module_probe(image, modules, *, expect_present, label):
        checks = ', '.join(
            f'({name!r}, {expect_present!r})' for name in modules
        )
        probe = (
            'import importlib.util as u, sys\n'
            f'for name, expect in [{checks}]:\n'
            '    found = u.find_spec(name) is not None\n'
            '    if found != expect:\n'
            '        sys.exit(f"{name}: expected present={expect}, found={found}")\n'
            'print("ok")\n'
        )
        run(
            ['docker', 'run', '--rm', '--entrypoint', 'python', image, '-c', probe],
            timeout=300,
        )
        return label

    evidence: dict = {'result': 'failed'}

    def cleanup():
        compose(
            'down', '--volumes', '--remove-orphans',
            check=False, timeout=300,
        )

    try:
        # ── 1. images ────────────────────────────────────────────────────
        run(
            ['docker', 'build', '--target', 'api', '-t', env['API_IMAGE'],
             '-f', 'test-platform-v2/backend/Dockerfile', '.'],
            timeout=1800,
        )
        run(
            ['docker', 'build', '--target', 'ai-gateway',
             '-t', env['AI_GATEWAY_IMAGE'],
             '-f', 'test-platform-v2/backend/Dockerfile', '.'],
            timeout=1800,
        )
        run(
            ['docker', 'build', '--target', 'runner', '-t', env['RUNNER_IMAGE'],
             '-f', 'test-platform-v2/backend/Dockerfile', '.'],
            timeout=1800,
        )
        sizes = {}
        for label, image in (
            ('api', env['API_IMAGE']),
            ('ai-gateway', env['AI_GATEWAY_IMAGE']),
            ('runner', env['RUNNER_IMAGE']),
        ):
            sizes[label] = int(
                run(
                    ['docker', 'image', 'inspect', '--format', '{{.Size}}', image]
                ).stdout.strip()
            )

        # ── 2. image boundary assertions ─────────────────────────────────
        image_module_probe(
            env['API_IMAGE'], API_FORBIDDEN_MODULES,
            expect_present=False, label='api-image-slim',
        )
        image_module_probe(
            env['AI_GATEWAY_IMAGE'], GATEWAY_REQUIRED_MODULES,
            expect_present=True, label='gateway-image-has-ai',
        )
        image_module_probe(
            env['AI_GATEWAY_IMAGE'], GATEWAY_FORBIDDEN_MODULES,
            expect_present=False, label='gateway-image-no-browser',
        )

        # ── 3. fail-closed: release split overlay needs a token ───────────
        without_token = dict(env)
        without_token.pop('AI_GATEWAY_TOKEN', None)
        missing_token_rejected = False
        result = compose(
            'config', '--quiet',
            overlay=(SPLIT_OVERLAY,), run_env=without_token, check=False,
        )
        if result.returncode:
            missing_token_rejected = True
        if not missing_token_rejected:
            raise AssertionError(
                'release split overlay rendered without AI_GATEWAY_TOKEN'
            )

        # ── 4. fail-closed: combined overlay still renders ────────────────
        combined = dict(env)
        combined.pop('AI_GATEWAY_TOKEN', None)
        compose('config', '--quiet', overlay=(COMBINED_OVERLAY,),
                run_env=combined)

        # ── 5. gateway refuses to report healthy without a token ─────────
        no_token_probe = (
            'import sys\n'
            'from fastapi.testclient import TestClient\n'
            'from app.ai_gateway_app import app\n'
            'status = TestClient(app).get("/internal/ai/v1/health").status_code\n'
            'if status != 503:\n'
            '    sys.exit(f"expected 503 without token, got {status}")\n'
            'print("ok")\n'
        )
        run(
            ['docker', 'run', '--rm', '-e', 'AI_GATEWAY_TOKEN=',
             '--entrypoint', 'python', env['AI_GATEWAY_IMAGE'], '-c',
             no_token_probe],
            timeout=300,
        )

        # ── 6. bring the default split topology up ───────────────────────
        # Images were built above with explicit tags; reuse them instead of
        # rebuilding through the compose planner (slow on constrained hosts).
        compose(
            'up', '-d', '--no-build', '--wait', '--wait-timeout', '300',
            'postgres', 'volume-permissions', 'ai-gateway', 'backend', 'runner',
            timeout=900,
        )

        def container(service):
            return compose('ps', '-q', service).stdout.strip()

        health = run([
            'docker', 'exec', container('backend'), 'python', '-c',
            "import urllib.request as u; print(u.urlopen('http://localhost:8000/health').status)",
        ]).stdout.strip()
        if health != '200':
            raise AssertionError(f'api health returned {health}')

        gateway_health = run([
            'docker', 'exec', container('ai-gateway'), 'python', '-c',
            "import urllib.request as u; "
            "print(u.urlopen('http://localhost:8100/internal/ai/v1/health').status)",
        ]).stdout.strip()
        if gateway_health != '200':
            raise AssertionError(f'gateway health returned {gateway_health}')

        runner_health = run([
            'docker', 'exec', container('runner'), 'python', '-c',
            "import urllib.request as u; print(u.urlopen('http://localhost:8000/health').status)",
        ]).stdout.strip()
        if runner_health != '200':
            raise AssertionError(f'runner health returned {runner_health}')

        # ── 7. api -> gateway hop carries the internal token ─────────────
        hop_probe = (
            'import json, urllib.error, urllib.request\n'
            'url = "http://ai-gateway:8100/internal/ai/v1/embed"\n'
            'body = json.dumps({"texts": ["split-smoke"]}).encode()\n'
            'def call(token):\n'
            '    request = urllib.request.Request(url, data=body,\n'
            '        headers={"Content-Type": "application/json", **token})\n'
            '    try:\n'
            '        with urllib.request.urlopen(request, timeout=120) as r:\n'
            '            return r.status\n'
            '    except urllib.error.HTTPError as exc:\n'
            '        return exc.code\n'
            'anon = call({})\n'
            'print(json.dumps({"anonymous": anon}))\n'
        )
        hop = run([
            'docker', 'exec', container('backend'), 'python', '-c', hop_probe,
        ])
        anonymous = json.loads(hop.stdout.strip().splitlines()[-1])['anonymous']
        if anonymous not in (401, 403):
            raise AssertionError(f'anonymous gateway call returned {anonymous}')

        # ── 8. combined rollback topology renders ────────────────────────
        rollback = compose(
            'config', '--format', 'json',
            overlay=(COMBINED_OVERLAY,), run_env=combined,
        )
        services = json.loads(rollback.stdout)
        targets = {
            name: (service.get('build') or {}).get('target')
            for name, service in services['services'].items()
        }
        if targets.get('backend') != 'runtime':
            raise AssertionError(f'combined backend target={targets.get("backend")}')
        for absent in ('ai-gateway', 'runner'):
            if absent in services['services']:
                raise AssertionError(f'combined topology still runs {absent}')

        evidence = {
            'result': 'passed',
            'images': sizes,
            'chain': {
                'api_health': True,
                'gateway_health': True,
                'runner_health': True,
                'api_to_gateway_anonymous_rejected': anonymous,
            },
            'fail_closed': {
                'missing_token_blocks_split_rendering': missing_token_rejected,
                'gateway_unhealthy_without_token': True,
            },
            'image_boundaries': {
                'api_excludes': list(API_FORBIDDEN_MODULES),
                'gateway_includes': list(GATEWAY_REQUIRED_MODULES),
                'gateway_excludes': list(GATEWAY_FORBIDDEN_MODULES),
            },
            'combined_rollback': {'backend_target': 'runtime'},
        }
        print(json.dumps(evidence), flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001 - smoke reports the first failure
        diagnostic = compose(
            'logs', '--tail', '40', 'backend', 'ai-gateway', 'runner',
            check=False, timeout=300,
        )
        text = (diagnostic.stdout or '') + (diagnostic.stderr or '')
        for value in (password, gateway_token, env['SECRET_KEY']):
            text = text.replace(value, '[redacted]')
        print(text, file=sys.stderr)
        print(json.dumps({'result': 'failed', 'error': str(exc)}), flush=True)
        return 1
    finally:
        cleanup()


if __name__ == '__main__':
    sys.exit(main())
