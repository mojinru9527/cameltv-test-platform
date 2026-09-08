"""Real kernel-lock tests independent of application/DB fixtures."""
from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
import tempfile
import threading
import time
import unittest

from app.core.resource_budget import FileBudget, BudgetCancelled, BudgetTimeout


def _hold_in_process(directory, ready):
    budget = FileBudget(Path(directory), 1)
    with budget.wait('browser', 'child', timeout=2):
        ready.set()
        time.sleep(20)


class FileBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_instances_share_capacity_and_release_after_exception(self):
        first = FileBudget(self.root, 1)
        second = FileBudget(self.root, 1)
        with self.assertRaisesRegex(ValueError, 'task failed'):
            with first.wait('ui', '1', timeout=0):
                self.assertIsNone(second.try_acquire('lanhu', '2'))
                raise ValueError('task failed')
        with second.wait('lanhu', '2', timeout=0):
            self.assertIsNone(first.try_acquire('ui', '3'))

    def test_capacity_two_releases_from_another_thread(self):
        budget = FileBudget(self.root, 2)
        one = budget.try_acquire('ui', '1')
        two = budget.try_acquire('dsh', '2')
        self.assertIsNone(budget.try_acquire('ocr', '3'))
        thread = threading.Thread(target=one.release)
        thread.start()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        with budget.wait('ocr', '3', timeout=0):
            self.assertIsNone(budget.try_acquire('embedding', '4'))
        one.release()
        two.release()

    def test_cancel_and_timeout_do_not_steal_or_leak_slot(self):
        budget = FileBudget(self.root, 1)
        cancelled = threading.Event()
        cancelled.set()
        with budget.wait('ui', 'owner', timeout=0):
            with self.assertRaises(BudgetCancelled):
                budget.wait('dsh', 'cancelled', timeout=1, cancelled=cancelled.is_set)
            with self.assertRaises(BudgetTimeout):
                budget.wait('dsh', 'timeout', timeout=0.02, poll_interval=0.01)
        with budget.wait('dsh', 'next', timeout=0):
            pass

    def test_different_capacity_fails_closed(self):
        one = FileBudget(self.root, 1)
        with one.wait('ui', '1', timeout=0):
            with self.assertRaisesRegex(ValueError, 'capacity'):
                FileBudget(self.root, 2).try_acquire('ui', '2')

    def test_child_crash_releases_kernel_lock_despite_running_metadata(self):
        context = multiprocessing.get_context('spawn')
        ready = context.Event()
        process = context.Process(target=_hold_in_process, args=(str(self.root), ready))
        process.start()
        try:
            self.assertTrue(ready.wait(10), 'child failed to acquire')
            budget = FileBudget(self.root, 1)
            self.assertIsNone(budget.try_acquire('ui', 'parent'))
            process.terminate()
            process.join(10)
            self.assertFalse(process.is_alive())
            with budget.wait('ui', 'after-crash', timeout=1):
                pass
        finally:
            if process.is_alive():
                process.terminate()
            process.join(10)
            process.close()

    def test_status_storage_is_bounded_and_memory_scope_is_explicit(self):
        budget = FileBudget(self.root, 1, sampler=lambda: ('container', 123))
        for number in range(12):
            with budget.wait('ui', str(number), timeout=0):
                pass
        files = list(self.root.glob('slot-*.json'))
        self.assertEqual(len(files), 1)
        state = json.loads(files[0].read_text())
        self.assertEqual(state['state'], 'released')
        self.assertEqual(state['observed_peak_bytes'], 123)
        self.assertEqual(state['memory_scope'], 'container')
        self.assertEqual(state['task_id'], '11')


if __name__ == '__main__':
    unittest.main()
