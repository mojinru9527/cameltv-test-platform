"""Validate the simplified deployment topology using Compose's actual merge rules.

平台简化批次：ai-gateway 独立服务与 aitde-worker 已删除，AI 走平台直连、
执行走 backend(API) + runner(执行) 双角色拓扑。本测试固化该契约，防止
已删除的服务/角色被悄悄带回或执行所有权被反转。
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which('docker'), 'Docker Compose required')
class DeployComposeTests(unittest.TestCase):
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
            # 凭据探针：必须给非空值，否则 `AI_API_KEY=` 渲染为空串，
            # 「Key 只在 backend」的断言会因两边都为空而**假通过**。
            'AI_API_KEY': 'sk-compose-validation-only',
            'DSH_API_KEY': 'sk-compose-validation-retired',
        })
        result = subprocess.run(
            ['docker', 'compose', '--env-file', os.devnull, '-f', 'docker-compose.yml', 'config', '--format', 'json'],
            cwd=ROOT / 'test-platform-v2/deploy', env=env,
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode:
            raise RuntimeError(f'Compose validation failed: {result.stderr}')
        cls.services = json.loads(result.stdout)['services']

    def test_deleted_topology_is_gone(self):
        """已删除的服务不得回到部署面。"""
        for gone in ('ai-gateway', 'aitde-worker'):
            self.assertNotIn(gone, self.services)

    def test_execution_ownership_and_startup_order(self):
        api, runner = self.services['backend'], self.services['runner']
        self.assertEqual(api['build']['target'], 'api')
        self.assertEqual(runner['build']['target'], 'runner')
        self.assertEqual(api['environment']['WORKER_EXECUTION_ENABLED'], 'false')
        self.assertEqual(runner['environment']['WORKER_EXECUTION_ENABLED'], 'true')
        # 平台简化批次：compose 不再覆盖启动命令，两个角色都用镜像默认 CMD
        # （先 alembic upgrade head 再起服务），避免命令在两处漂移。
        self.assertIsNone(api.get('command'))
        self.assertIsNone(runner.get('command'))
        self.assertNotIn('ports', runner)

    def test_ai_runs_in_platform_process(self):
        """AI 直连模式：Key 与开关只出现在 backend，不再有独立网关容器。"""
        api = self.services['backend']
        self.assertIn('AI_API_KEY', api['environment'])
        self.assertNotIn('AI_GATEWAY_URL', api['environment'])
        self.assertNotIn('AI_GATEWAY_ROLE', api['environment'])

    def test_cloud_ai_key_is_not_inherited_by_runner(self):
        """P0-4 凭据最小化：`runner` 经 `extends` 继承 backend 环境，必须显式清空 AI Key。

        这是渲染后拓扑的断言（而非原始 YAML）：只有校验 merge/extends 结果，才能发现
        「Key 被悄悄复制进执行容器」这类回归。
        """
        holders = {
            name
            for name, service in self.services.items()
            if (service.get('environment') or {}).get('AI_API_KEY')
        }
        self.assertEqual(holders, {'backend'})
        retired = {
            name
            for name, service in self.services.items()
            if (service.get('environment') or {}).get('DSH_API_KEY')
        }
        self.assertEqual(retired, set(), 'DSH 已删除，其 Key 不得出现在任何服务')

    def test_single_database_and_shared_volumes(self):
        for name in ('backend', 'runner', 'volume-permissions'):
            self.assertIn(name, self.services)
        mounts = []
        for name in ('backend', 'runner', 'volume-permissions'):
            volumes = {v['target']: v['source'] for v in self.services[name]['volumes']}
            mounts.append(volumes.get('/app/storage'))
        self.assertTrue(all(mount == mounts[0] for mount in mounts))


if __name__ == '__main__':
    unittest.main()
