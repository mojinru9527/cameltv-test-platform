import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tencent_executor import ExecutorCommandFailed, ExecutorConfig, TencentSshExecutor


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

    def split_manifest(self):
        return {'release_id': 'release-20260907-0001', 'runtime_mode': 'split',
                'runner': {'image': 'cameltv-tp-runner', 'digest': 'sha256:' + 'a' * 64},
                'execution_config_sha256': 'b' * 64}

    def test_split_verification_precedes_import_and_all_imports_precede_stop(self):
        with patch.object(self.executor, '_run_remote', return_value='ok') as run:
            self.executor.deploy('release-20260907-0001', manifest=self.split_manifest())
        commands = run.call_args.args[0]
        first_load = next(i for i, command in enumerate(commands) if command.startswith('docker load'))
        self.assertEqual(sum(c.startswith('docker load') for c in commands), 3)
        self.assertTrue(commands[2].startswith('python3 -c '))
        self.assertTrue(any('config --quiet' in c for c in commands[:first_load]))
        stop = next(i for i, c in enumerate(commands) if 'stop --timeout' in c)
        self.assertTrue(all(i < stop for i, c in enumerate(commands) if c.startswith('docker load')))
        self.assertIn('aitde-worker', commands[stop])
        activation = next(c for c in commands if 'up -d' in c)
        self.assertIn('docker-compose.execution.release-20260907-0001.yml', activation)
        self.assertIn('--wait', activation)
        self.assertIn('runner backend frontend aitde-worker', activation)

    def test_split_rollback_checks_complete_set_before_retagging(self):
        with patch.object(self.executor, '_run_remote', return_value='ok') as run:
            self.executor.rollback('release-20260907-0001', manifest=self.split_manifest())
        commands = run.call_args.args[0]
        first_tag = next(i for i, c in enumerate(commands) if c.startswith('docker tag'))
        self.assertEqual(sum(c.startswith('docker image inspect') for c in commands[:first_tag]), 3)
        self.assertTrue(any('sha256sum' in c for c in commands[:first_tag]))
        self.assertFalse(any('|| true' in c for c in commands))

    def test_manifest_tag_mismatch_never_reaches_ssh(self):
        with patch.object(self.executor, '_run_remote') as run:
            for operation in (self.executor.deploy, self.executor.rollback):
                with self.assertRaises(ExecutorCommandFailed):
                    operation('release-20260908-0001', manifest=self.split_manifest())
        run.assert_not_called()

    def test_rollback_skips_old_image_migration_launcher(self):
        for manifest in (None, self.split_manifest()):
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


if __name__ == '__main__':
    unittest.main()
