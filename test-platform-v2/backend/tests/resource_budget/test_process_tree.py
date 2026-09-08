"""Run with stdlib unittest in a disposable Linux container as well as pytest."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from app.core.process_tree import run_supervised


@unittest.skipUnless(sys.platform == 'linux', 'production Linux process groups')
class ProcessTreeTests(unittest.TestCase):
    def assert_stopped(self, pid):
        for _ in range(100):
            path = Path(f'/proc/{pid}/stat')
            if not path.exists():
                return
            try:
                if path.read_text().split(') ', 1)[1].split()[0] == 'Z':
                    return
            except FileNotFoundError:
                return
            time.sleep(0.02)
        self.fail(f'child {pid} still running')

    def run_parent(self, sleep_seconds, timeout):
        with tempfile.TemporaryDirectory() as tmp:
            pid_path = Path(tmp) / 'child.pid'
            source = (
                'import subprocess, sys, time; from pathlib import Path; '
                "p=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], "
                'stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); '
                'Path(sys.argv[1]).write_text(str(p.pid)); '
                f'time.sleep({sleep_seconds})'
            )
            try:
                return run_supervised([sys.executable, '-c', source, str(pid_path)],
                                      timeout=timeout, text=True)
            finally:
                self.assertTrue(pid_path.exists(), 'parent did not start child')
                child_pid = int(pid_path.read_text())
                try:
                    self.assert_stopped(child_pid)
                finally:
                    try:
                        os.kill(child_pid, 9)
                    except ProcessLookupError:
                        pass

    def test_timeout_terminates_descendants(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_parent(60, 1)

    def test_success_also_removes_lingering_descendants(self):
        result = self.run_parent(0, 3)
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
