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


if __name__ == '__main__':
    unittest.main()
