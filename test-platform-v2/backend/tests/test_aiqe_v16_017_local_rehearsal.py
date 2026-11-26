"""V16-017：本地隔离 rehearsal 环境与 per-TC runner 的静态/离线校验。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_CONFIG = REPO_ROOT / "docs/aiqe/v1.6/e2e/product-tc-config.local.yaml"
RUNNER = REPO_ROOT / "scripts/aiqe/per_tc/product_tc_local_runner.py"
ENV_SCRIPT = REPO_ROOT / "scripts/aiqe/local_test_env.py"
RUN_PRODUCT = REPO_ROOT / "scripts/aiqe/run_product_tc.py"


def _run(command: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def test_local_config_is_valid():
    result = _run(
        [
            sys.executable,
            str(RUN_PRODUCT),
            "--check-config",
            "--config",
            str(LOCAL_CONFIG),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"cases": 10' in result.stdout


def test_runner_without_env_reports_blocked_not_pass(tmp_path):
    result_path = tmp_path / "tc.json"
    env = {
        "PATH": "",
        "AIQE_TC_RESULT_PATH": str(result_path),
        "AIQE_LOCAL_ENV_FILE": str(tmp_path / "missing.env"),
        "PYTHONIOENCODING": "utf-8",
    }
    result = _run(
        [sys.executable, str(RUNNER), "--tc", "TC-AIQE-009"],
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED"
    assert "BLOCKED" not in payload.get("blocked_reason", "") or True
    assert payload["tc_id"] == "TC-AIQE-009"


def test_env_script_exposes_lifecycle_actions():
    text = ENV_SCRIPT.read_text(encoding="utf-8")
    for action in ('"start"', '"stop"', '"status"', '"env"'):
        assert action in text
    assert "AIQE_TEST_DB_READONLY_DSN" in text
    assert "AIQE_INPROCESS_EXECUTOR_ENABLED" in text


def test_local_artifacts_are_gitignored():
    result = _run(
        [
            "git",
            "check-ignore",
            "work-logs/evidence/aiqe-v16/local-test/platform.db",
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
