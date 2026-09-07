import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import capacity


class CapacityTests(unittest.TestCase):
    def test_upload_accounts_for_archive_and_import(self):
        self.assertEqual(capacity.required_bytes(3 * capacity.GIB, 'upload'), 11 * capacity.GIB)
        self.assertEqual(capacity.required_bytes(3 * capacity.GIB, 'import'), 8 * capacity.GIB)

    def test_invalid_sizes_and_stages_fail(self):
        for value in (0, -1):
            with self.assertRaises(ValueError):
                capacity.required_bytes(value, 'upload')
        with self.assertRaises(ValueError):
            capacity.required_bytes(1, 'unknown')

    def test_capacity_boundary_and_inodes(self):
        capacity.validate_space(8 * capacity.GIB, 10000, 100000, 8 * capacity.GIB)
        with self.assertRaises(RuntimeError):
            capacity.validate_space(8 * capacity.GIB - 1, 10000, 100000, 8 * capacity.GIB)
        with self.assertRaises(RuntimeError):
            capacity.validate_space(20 * capacity.GIB, 1000, 100000, 8 * capacity.GIB)

    def test_remote_command_does_not_interpolate_paths(self):
        command = capacity.remote_check_command('/opt/a $(touch nope)', 'release-20260907-0001')
        self.assertNotIn('$(touch nope)', command)
        self.assertTrue(command.startswith('python3 -c '))

    def test_real_archive_sizes_and_same_device_are_checked_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for part in ('backend', 'frontend'):
                (root / f'release-20260907-0001-{part}.tar').write_bytes(b'archive')
            with patch.object(capacity.subprocess, 'check_output', return_value=tmp), \
                    patch.object(capacity.shutil, 'disk_usage', return_value=SimpleNamespace(free=20 * capacity.GIB)), \
                    patch.object(capacity.os, 'statvfs', create=True,
                                 return_value=SimpleNamespace(f_favail=10000, f_files=100000)):
                result = capacity.check(tmp, 'import', tag='release-20260907-0001')
            self.assertEqual(result['archive_bytes'], 14)
            self.assertTrue(result['ok'])
            self.assertEqual(len(result['filesystems']), 1)

    def test_missing_archive_rejected_before_docker_inspection(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(capacity.subprocess, 'check_output') as run:
            with self.assertRaises(ValueError):
                capacity.check(tmp, 'import', tag='release-20260907-0001')
            run.assert_not_called()

    def test_docker_inspection_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(capacity.subprocess, 'check_output',
                             side_effect=subprocess.CalledProcessError(1, 'docker')):
            with self.assertRaises(subprocess.CalledProcessError):
                capacity.check(tmp, 'upload', archive_bytes=100)


if __name__ == '__main__':
    unittest.main()
