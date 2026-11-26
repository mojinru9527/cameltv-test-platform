"""V16-017 产品级 TC 执行编排（run_product_tc.py）与 Gate E 联动。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/run_product_tc.py"
CONFIG = REPO_ROOT / "docs/aiqe/v1.6/e2e/product-tc-config.yaml"
TC_IDS = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load(SCRIPT, "run_product_tc")


def _valid_record(tc_id: str) -> dict:
    return {
        "tc_id": tc_id,
        "status": "PASS",
        "run_id": f"run-{tc_id}",
        "project_id": 1,
        "workflow_snapshot_hash": "a" * 64,
        "job_ids": [1],
        "node_run_ids": ["n-1"],
        "assertion_ids": ["a-1"],
        "artifact_refs": ["art-1"],
        "blocked_reason": "",
        "duration_ms": 1,
    }


def test_config_covers_all_product_tcs():
    config = MODULE.load_config(CONFIG)
    assert MODULE.validate_config(config) == []
    assert {case["tc_id"] for case in config["test_cases"]} == set(TC_IDS)


def test_run_without_env_is_not_proven():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--run"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 2
    assert "NOT_PROVEN" in result.stdout


def _write_fake_runner(tmp_path: Path, *, status: str = "PASS") -> Path:
    script = tmp_path / "fake_tc_runner.py"
    script.write_text(
        "import json, os, sys\n"
        "tc_id = sys.argv[1]\n"
        f"record = {json.dumps(_valid_record('PLACEHOLDER'))}\n"
        "record['tc_id'] = tc_id\n"
        f"record['status'] = {status!r}\n"
        "if record['status'] != 'PASS':\n"
        "    record['blocked_reason'] = 'fixture-fail'\n"
        "open(os.environ['AIQE_TC_RESULT_PATH'], 'w', encoding='utf-8').write(\n"
        "    json.dumps(record))\n",
        encoding="utf-8",
    )
    return script


def _config_with_runner(runner: Path, tmp_path: Path) -> Path:
    cases = []
    for tc_id in TC_IDS:
        cases.append(
            {
                "tc_id": tc_id,
                "title": tc_id,
                "spec_ref": "merged-spec §20",
                "runner": [sys.executable, str(runner), tc_id],
                "evidence_glob": "docs/aiqe/v1.6/evidence/product/**",
                "blocked_by": "",
            }
        )
    config = {
        "schema_version": "1.0",
        "environment": "unit-fake",
        "required_env": [],
        "test_cases": cases,
    }
    path = tmp_path / "config.yaml"
    import yaml

    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return path


def test_run_with_fake_runners_aggregates_pass(tmp_path):
    runner = _write_fake_runner(tmp_path)
    config = _config_with_runner(runner, tmp_path)
    output = tmp_path / "product-results.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run",
            "--config",
            str(config),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["product_tc_pass"] == 10
    assert payload["summary"]["ga_ready"] is True
    assert {item["tc_id"] for item in payload["tests"]} == set(TC_IDS)


def test_run_with_failed_runner_is_nonzero(tmp_path):
    runner = _write_fake_runner(tmp_path, status="BLOCKED")
    config = _config_with_runner(runner, tmp_path)
    output = tmp_path / "product-results.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run",
            "--config",
            str(config),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["product_tc_pass"] == 0
    assert payload["summary"]["BLOCKED"] == 10


def test_config_rejects_missing_tc(tmp_path):
    config = MODULE.load_config(CONFIG)
    config["test_cases"] = [case for case in config["test_cases"] if case["tc_id"] != "TC-AIQE-010"]
    errors = MODULE.validate_config(config)
    assert any("TC-AIQE-010" in item for item in errors)
