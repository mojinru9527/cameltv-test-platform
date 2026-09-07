"""UI admission must leave business tasks pending while another workload runs."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.core.resource_budget import FileBudget
from app.services import playwright_executor as executor


class UiAdmissionTests(unittest.TestCase):
    def test_other_workload_prevents_claim_and_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            budget = FileBudget(Path(tmp), 1)
            with budget.wait('lanhu', 'lanhu:1', timeout=0), \
                    patch.object(executor, 'configured_budget', return_value=budget), \
                    patch.object(executor, '_current_run_status', return_value='pending'), \
                    patch.object(executor, '_claim_pending_run') as claim, \
                    patch.object(executor, '_run_playwright_test') as run:
                result = executor.run_playwright_test(Mock(), 1, 2, 3)
            self.assertEqual(result['status'], 'pending')
            claim.assert_not_called()
            run.assert_not_called()
            with budget.wait('dsh', 'dsh:1', timeout=0):
                pass

    def test_failed_claim_releases_shared_and_local_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            budget = FileBudget(Path(tmp), 1)
            with patch.object(executor, 'configured_budget', return_value=budget), \
                    patch.object(executor, '_claim_pending_run', return_value=False), \
                    patch.object(executor, '_current_run_status', return_value='cancelled'):
                for _ in range(executor.MAX_CONCURRENT + 1):
                    self.assertEqual(executor.run_playwright_test(Mock(), 1, 2, 3)['status'], 'cancelled')
            with budget.wait('lanhu', 'lanhu:1', timeout=0):
                pass

    def test_exception_in_claim_releases_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            budget = FileBudget(Path(tmp), 1)
            with patch.object(executor, 'configured_budget', return_value=budget), \
                    patch.object(executor, '_claim_pending_run', side_effect=RuntimeError('db unavailable')):
                with self.assertRaises(RuntimeError):
                    executor.run_playwright_test(Mock(), 1, 2, 3)
            with budget.wait('dsh', 'dsh:1', timeout=0):
                pass


if __name__ == '__main__':
    unittest.main()
