"""Validate the opt-in execution deployment using Compose's actual merge rules."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which('docker'), 'Docker Compose required')
class ExecutionComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {key: value for key, value in os.environ.items()
               if key.upper() in {'PATH', 'SYSTEMROOT', 'COMSPEC', 'TEMP', 'TMP',
                                  'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
                                  'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
                                  'PROGRAMW6432', 'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_CONFIG'}}
        env.update({
            'POSTGRES_PASSWORD': 'compose-validation-only',
            'ENVIRONMENT': 'development', 'SECRET_KEY': 'compose-validation-only',
            'ADMIN_PASSWORD': 'compose-validation-only', 'TESTER_PASSWORD': 'compose-validation-only',
            'COOKIE_SECURE': 'false', 'DATABASE_URL': 'sqlite:////data/compose-test.db',
            'API_IMAGE': 'cameltv-tp-api:capacity-local', 'RUNNER_IMAGE': 'cameltv-tp-runner:capacity-local',
            'API_MEMORY_LIMIT': '512m', 'RUNNER_MEMORY_LIMIT': '1536m',
            'TEMPORAL_WORKER_MEMORY_LIMIT': '512m',
        })
        result = subprocess.run(
            ['docker', 'compose', '--profile', 'aitde-worker', '--env-file', os.devnull, '-f', 'docker-compose.yml',
             '-f', 'docker-compose.execution.yml', 'config', '--format', 'json'],
            cwd=ROOT / 'test-platform-v2/deploy', env=env,
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode:
            raise RuntimeError(f'Compose validation failed: {result.stderr}')
        cls.services = json.loads(result.stdout)['services']

    def test_execution_owners_and_startup_order(self):
        api, runner = self.services['backend'], self.services['runner']
        self.assertEqual(api['build']['target'], 'api')
        self.assertEqual(runner['build']['target'], 'runner')
        self.assertEqual(api['environment']['WORKER_EXECUTION_ENABLED'], 'false')
        self.assertEqual(runner['environment']['WORKER_EXECUTION_ENABLED'], 'true')
        self.assertEqual(api['depends_on']['runner']['condition'], 'service_healthy')
        self.assertNotIn('runner', runner['depends_on'])
        self.assertNotIn('backend', runner['depends_on'])
        self.assertEqual(api['command'][0], 'uvicorn')
        self.assertIsNone(runner.get('command'))  # Image default performs migrations first.
        self.assertNotIn('ports', runner)

    def test_artifacts_specs_and_budget_share_same_named_volumes(self):
        targets = ('/data', '/app/storage', '/app/tests/playwright/specs/generated',
                   '/app/tests/playwright/generated')
        mounts = []
        for name in ('backend', 'runner', 'aitde-worker', 'volume-permissions'):
            volumes = {v['target']: v['source'] for v in self.services[name]['volumes']}
            mounts.append({target: volumes[target] for target in targets})
        self.assertTrue(all(mount == mounts[0] for mount in mounts))
        for name in ('runner', 'aitde-worker'):
            env = self.services[name]['environment']
            self.assertEqual(env['HEAVY_TASK_BUDGET_DIR'], '/app/storage/resource-budget')
            self.assertEqual(env['HEAVY_TASK_BUDGET_CAPACITY'], '1')
            self.assertEqual(env['HEAVY_TASK_BUDGET_ENABLED'], 'true')

    def test_temporal_keeps_runner_runtime_and_limits_are_applied(self):
        worker = self.services['aitde-worker']
        self.assertEqual(worker['build']['target'], 'runner')
        self.assertEqual(worker['command'][0], '/usr/local/bin/start-aitde-worker')
        self.assertEqual(worker['environment']['WORKER_EXECUTION_ENABLED'], 'true')
        for name in ('backend', 'runner', 'aitde-worker'):
            self.assertGreater(int(self.services[name]['mem_limit']), 0)
            self.assertGreater(self.services[name]['pids_limit'], 0)
            self.assertTrue(self.services[name]['init'])


if __name__ == '__main__':
    unittest.main()
