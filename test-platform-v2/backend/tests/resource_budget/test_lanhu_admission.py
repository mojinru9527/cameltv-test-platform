from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.core.resource_budget import FileBudget
from app.services.lanhu_evidence import worker


class LanhuAdmissionTests(unittest.TestCase):
    def test_busy_budget_leaves_job_unclaimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            budget = FileBudget(Path(tmp), 1)
            with budget.wait('ui', 'ui:1', timeout=0), \
                    patch.object(worker, 'configured_budget', return_value=budget), \
                    patch.object(worker.settings, 'lanhu_evidence_worker_enabled', True), \
                    patch.object(worker, 'SessionLocal', return_value=Mock()), \
                    patch.object(worker, 'recover_stale_jobs'), \
                    patch.object(worker, 'claim_next_job') as claim:
                worker.poll_and_execute_evidence_jobs()
            claim.assert_not_called()
            with budget.wait('ui', 'ui:2', timeout=0):
                pass

    def test_empty_poll_releases_slot_and_starts_no_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            budget = FileBudget(Path(tmp), 1)
            with patch.object(worker, 'configured_budget', return_value=budget), \
                    patch.object(worker.settings, 'lanhu_evidence_worker_enabled', True), \
                    patch.object(worker, 'SessionLocal', return_value=Mock()), \
                    patch.object(worker, 'recover_stale_jobs'), \
                    patch.object(worker, 'claim_next_job', return_value=None):
                worker.poll_and_execute_evidence_jobs()
            with budget.wait('ui', 'ui:2', timeout=0):
                pass


if __name__ == '__main__':
    unittest.main()
