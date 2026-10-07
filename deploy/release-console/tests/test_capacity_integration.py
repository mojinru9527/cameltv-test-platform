import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tencent_executor import (  # noqa: E402 - conftest.py 已加路径
    ExecutorCommandFailed,
    ExecutorConfig,
    TencentSshExecutor,
    release_parts,
    rollback_runtime_override,
)


class ExecutorCapacityTests(unittest.TestCase):
    def setUp(self):
        self.executor = TencentSshExecutor(ExecutorConfig(
            host='test', user='test', ssh_key_b64='', compose_dir='/opt/compose',
            release_dir='/opt/releases', backup_dir='/opt/backups',
            image_backend='cameltv-tp-backend:main',
            image_frontend='cameltv-tp-frontend:main', compose_project='test'))

    def test_admission_precedes_docker_load_under_shared_lock(self):
        with patch.object(self.executor, '_run_remote', return_value='ok') as run:
            self.executor.deploy('release-20260907-0001')
        commands = run.call_args.args[0]
        self.assertIn('flock -n 9', commands[0])
        self.assertTrue(commands[1].startswith('python3 -c '))
        self.assertTrue(commands[2].startswith('docker load'))

    def test_failed_remote_admission_never_reports_success(self):
        with patch.object(self.executor, '_run_remote', side_effect=ExecutorCommandFailed('disk full')):
            with self.assertRaises(ExecutorCommandFailed):
                self.executor.deploy('release-20260907-0001')

    def test_rollback_uses_lock_without_capacity_requirement(self):
        with patch.object(self.executor, '_run_remote', return_value='ok') as run:
            self.executor.rollback('release-20260906-0001')
        commands = run.call_args.args[0]
        self.assertIn('flock -n 9', commands[0])
        self.assertFalse(any(c.startswith('python3 -c ') for c in commands))

    def manifest(self):
        """简化后只有一套拓扑：split 标签仍被接受，但制品集与 combined 相同。"""
        return {'release_id': 'release-20260907-0001', 'runtime_mode': 'split',
                # Batch 249：发布必须携带真实 alembic revision（ADR-0015 §4）
                'database': {'target_revision': '20260922_ai_agent_token'},
                'runner': {'image': 'cameltv-tp-runner', 'digest': 'sha256:' + 'a' * 64},
                'execution_config_sha256': 'b' * 64}

    def test_release_verification_precedes_import_and_all_imports_precede_stop(self):
        with patch.object(self.executor, '_run_remote', return_value='ok') as run:
            self.executor.deploy('release-20260907-0001', manifest=self.manifest())
        commands = run.call_args.args[0]
        first_load = next(i for i, command in enumerate(commands) if command.startswith('docker load'))
        self.assertEqual(sum(c.startswith('docker load') for c in commands), 3)
        self.assertEqual(first_load, 3)
        self.assertTrue(commands[2].startswith('python3 -c '))
        stop = next(i for i, c in enumerate(commands) if 'stop --timeout' in c)
        self.assertTrue(all(i < stop for i, c in enumerate(commands) if c.startswith('docker load')))
        self.assertIn('stop --timeout 60 backend frontend runner', commands[stop])
        activation = next(c for c in commands if 'up -d' in c)
        self.assertIn('--wait', activation)
        self.assertIn('up -d --no-build --force-recreate --wait --wait-timeout 180 backend frontend runner',
                      activation)

    def test_both_runtime_modes_render_the_same_topology(self):
        """简化后 combined/split 只是标签：渲染出的文件与服务集完全一致。"""
        self.assertEqual(release_parts('split'), release_parts('combined'))
        self.assertEqual(sorted(release_parts('combined')), ['backend', 'frontend', 'runner'])
        rendered = []
        for manifest in (None, self.manifest()):
            with patch.object(self.executor, '_run_remote', return_value='ok') as run:
                self.executor.deploy('release-20260907-0001', manifest=manifest)
            commands = run.call_args.args[0]
            rendered.append((next(c for c in commands if 'up -d' in c),
                             next(c for c in commands if 'stop --timeout' in c)))
        self.assertEqual(rendered[0], rendered[1])
        for activation, stop in rendered:
            for command in (activation, stop):
                # 只有 base + override 两个 -f，且 compose 前不再注入任何 IMAGE_* 变量。
                self.assertEqual(command.count(' -f '), 2)
                self.assertIn('-f docker-compose.yml -f docker-compose.override.yml', command)
                self.assertIn('&& docker compose --project-name', command)
            self.assertIn('stop --timeout 60 backend frontend runner', stop)

    def test_rollback_checks_complete_set_before_retagging(self):
        with patch.object(self.executor, '_run_remote', return_value='ok') as run:
            self.executor.rollback('release-20260907-0001', manifest=self.manifest())
        commands = run.call_args.args[0]
        first_tag = next(i for i, c in enumerate(commands) if c.startswith('docker tag'))
        self.assertEqual(sum(c.startswith('docker image inspect') for c in commands[:first_tag]), 3)
        self.assertEqual(sum(c.startswith('docker tag') for c in commands), 3)
        self.assertFalse(any('|| true' in c for c in commands))

    def test_manifest_tag_mismatch_never_reaches_ssh(self):
        with patch.object(self.executor, '_run_remote') as run:
            for operation in (self.executor.deploy, self.executor.rollback):
                with self.assertRaises(ExecutorCommandFailed):
                    operation('release-20260908-0001', manifest=self.manifest())
        run.assert_not_called()

    def test_rollback_skips_old_image_migration_launcher(self):
        for manifest in (None, self.manifest()):
            with self.subTest(split=manifest is not None):
                with patch.object(self.executor, '_run_remote', return_value='ok') as run:
                    self.executor.rollback('release-20260907-0001', manifest=manifest)
                commands = run.call_args.args[0]
                activation = next(c for c in commands if 'up -d' in c)
                self.assertIn('docker-compose.rollback-runtime.yml', activation)
                validation = next(i for i, c in enumerate(commands) if 'rollback-runtime.yml' in c and 'config --quiet' in c)
                stop = next(i for i, c in enumerate(commands) if 'stop --timeout' in c)
                self.assertLess(validation, stop)
                self.assertTrue(any('uvicorn' in c and 'app.main:app' in c for c in commands))
                # 回滚绝不跑旧镜像的 Alembic：backend 与 runner 都写显式启动命令。
                self.assertFalse(any('alembic' in c for c in commands))
        override = rollback_runtime_override('split')
        self.assertEqual(override, rollback_runtime_override('combined'))
        self.assertEqual(sorted(override['services']), ['backend', 'runner'])
        for service in override['services'].values():
            self.assertEqual(service['command'][:4], ['uvicorn', 'app.main:app', '--host', '0.0.0.0'])


if __name__ == '__main__':
    unittest.main()
