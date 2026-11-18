"""Test external_e2e node executor contract."""
from __future__ import annotations

import sys

from app.aiqe.services.node_executor import _execute_external_e2e


def test_external_e2e_success_exposes_result_and_json(tmp_path):
    out = _execute_external_e2e(
        {
            "command": [sys.executable, "-c", "print('ok')"],
            "version": "test-1",
            "cwd": str(tmp_path),
            "timeout_s": 30,
            "artifacts_dir": str(tmp_path),
        }
    )
    assert out.status == "PASSED"
    assert out.data["result"] == "PASS"
    assert out.data["json"]["result"] == "PASS"


def test_external_e2e_requires_pinned_version(tmp_path):
    out = _execute_external_e2e(
        {
            "command": [sys.executable, "-c", "print('ok')"],
            "cwd": str(tmp_path),
        }
    )
    assert out.status == "FAILED"
    assert out.error_class == "INPUT_INVALID"
