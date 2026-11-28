"""V16-017 / FIX-002：产品 TC 统一 Runner 执行编排与配置合同测试。"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/run_product_tc.py"
VERIFY_SCRIPT = REPO_ROOT / "scripts/aiqe/verify_product_tc_results.py"
CONFIG = REPO_ROOT / "docs/aiqe/v1.6/e2e/product-tc-config.yaml"
TC_IDS = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))
SHA = "a" * 40

FAKE_RUNNER = '''\
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.environ["AIQE_AIQE_SCRIPTS_DIR"])
from per_tc.runner_contract import (  # noqa: E402
    artifact_entry,
    assertion_result,
    execution_block,
    non_pass_record,
    pass_record,
    write_result,
)

tc_id = os.environ["AIQE_TC_ID"]
root = Path(os.environ["AIQE_TC_ROOT"])
result_path = os.environ["AIQE_TC_RESULT_PATH"]
commit = os.environ["AIQE_TESTED_COMMIT_SHA"]
environment = os.environ["AIQE_TC_ENVIRONMENT"]
mode = os.environ.get("FAKE_TC_MODE", "pass")

if mode == "legacy-pass":
    write_result(result_path, {
        "tc_id": tc_id,
        "status": "PASS",
        "run_id": "legacy-run",
        "project_id": 1,
        "workflow_snapshot_hash": "a" * 64,
        "job_ids": [1],
        "node_run_ids": ["node-1"],
        "assertion_ids": ["assert-1"],
        "artifact_refs": ["artifact-1"],
        "blocked_reason": "",
        "duration_ms": 1,
    })
    raise SystemExit(0)
if mode == "fail":
    write_result(result_path, non_pass_record(tc_id, status="FAIL", reason="fixture business assertion failed"))
    raise SystemExit(1)
if mode == "blocked":
    write_result(result_path, non_pass_record(tc_id, status="BLOCKED", reason="fixture environment missing"))
    raise SystemExit(0)
if mode == "no-result":
    raise SystemExit(0)

artifact_rel = f"artifacts/{tc_id}.txt"
artifact_path = root / artifact_rel
artifact_path.parent.mkdir(parents=True, exist_ok=True)
artifact_path.write_text(f"{tc_id} trace {commit}\\n", encoding="utf-8")
started = datetime.now(UTC) - timedelta(seconds=2)
finished = datetime.now(UTC)
execution = execution_block(
    run_id=f"run-{tc_id}",
    job_id=f"job-{tc_id}",
    tested_commit_sha=commit,
    environment=environment,
    started_at=started,
    finished_at=finished,
)
artifact = artifact_entry("trace", "trace", artifact_rel, root=root)
record = pass_record(
    tc_id,
    runner={
        "name": "fake_tc_runner",
        "type": "external_runner",
        "version": "1.0.0",
        "entrypoint": "scripts/fake_tc_runner.py",
    },
    execution=execution,
    assertions=[assertion_result("assert.ok", evidence_ref=artifact_rel)],
    artifacts=[artifact],
    baseline_version="v1.6.2-hardening",
    root=root,
)
write_result(result_path, record)
'''


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load(SCRIPT, "run_product_tc")


def _run(args: list[str], *, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=300,
    )


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _fixture_config(*, runner_entrypoint: str | None = "scripts/fake_tc_runner.py") -> dict:
    cases = []
    for tc_id in TC_IDS:
        case = {
            "tc_id": tc_id,
            "title": f"{tc_id} fixture",
            "spec_ref": "merged-spec §20",
            "baseline_version": "v1.6.2-hardening",
            "required_environment": "isolated-test",
            "required_assertions": ["assert.ok"],
            "required_artifacts": ["trace"],
            "timeout_seconds": 120,
        }
        if runner_entrypoint is None:
            case.update(
                {
                    "runner": None,
                    "blocked_status": "BLOCKED",
                    "blocked_by": "fixture blocks",
                    "owner": "qa-automation",
                    "unblock_action": "fixture unblock",
                }
            )
        else:
            case["runner"] = {
                "type": "external_runner",
                "entrypoint": runner_entrypoint,
                "version": "1.0.0",
            }
        cases.append(case)
    return {
        "schema_version": "2.0",
        "baseline_version": "v1.6.2-hardening",
        "environment": "isolated-test",
        "test_cases": cases,
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    runner = tmp_path / "scripts/fake_tc_runner.py"
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text(FAKE_RUNNER, encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    _write_yaml(config_path, _fixture_config())
    return tmp_path, config_path


def test_config_covers_all_product_tcs():
    config = MODULE.load_config(CONFIG)
    assert MODULE.validate_config(config) == []
    assert {case["tc_id"] for case in config["test_cases"]} == set(TC_IDS)
    assert config["schema_version"] == "2.0"
    assert config["baseline_version"] == "v1.6.2-hardening"
    assert config["environment"] == "isolated-test"


def test_config_null_runners_have_explicit_blocked_metadata():
    config = MODULE.load_config(CONFIG)
    for case in config["test_cases"]:
        for field in (
            "title",
            "spec_ref",
            "baseline_version",
            "required_environment",
            "required_assertions",
            "required_artifacts",
            "timeout_seconds",
        ):
            assert case.get(field), f"{case['tc_id']} 缺少 {field}"
        assert case["runner"] is None
        for field in ("blocked_by", "owner", "unblock_action"):
            assert str(case.get(field) or "").strip(), f"{case['tc_id']} 缺少 {field}"
        assert case["blocked_status"] == "BLOCKED"


def test_check_config_prints_config_valid_without_pass():
    result = _run(["--check-config"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CONFIG_VALID" in result.stdout
    assert "PASS" not in result.stdout.upper()


def test_plan_lists_ten_tcs_without_writing_results(tmp_path):
    output = tmp_path / "results.json"
    result = _run(["--plan", "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert [case["tc_id"] for case in payload["cases"]] == list(TC_IDS)
    assert payload["summary"]["total"] == 10
    assert all(case["planned_status"] == "BLOCKED" for case in payload["cases"])
    assert not output.exists()


def test_run_without_env_is_not_proven(tmp_path):
    output = tmp_path / "product-results.json"
    result = _run(["--run", "--output", str(output)])
    assert result.returncode == 2, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["baseline_version"] == "v1.6.2-hardening"
    assert len(payload["commit_sha"]) == 40
    assert payload["summary"]["product_tc_pass"] == 0
    assert payload["summary"]["BLOCKED"] == 10
    assert payload["verification"]["verified"] is False
    assert all(item["status"] == "BLOCKED" for item in payload["tests"])
    assert all(item["blocked_reason"] for item in payload["tests"])


def test_run_with_fake_runners_aggregates_pass(tmp_path):
    root, config_path = _fixture(tmp_path)
    output = root / "product-results.json"
    result = _run(
        ["--run", "--config", str(config_path), "--output", str(output), "--root", str(root)],
        env_extra={"AIQE_TESTED_COMMIT_SHA": SHA},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["product_tc_pass"] == 10
    assert payload["summary"]["ga_ready"] is True
    assert {item["tc_id"] for item in payload["tests"]} == set(TC_IDS)
    assert payload["verification"]["verified"] is False
    verify = subprocess.run(
        [
            sys.executable,
            str(VERIFY_SCRIPT),
            "--config",
            str(config_path),
            "--results",
            str(output),
            "--root",
            str(root),
            "--expected-commit",
            SHA,
            "--require-pass",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    verified = json.loads(output.read_text(encoding="utf-8"))
    assert verified["verification"]["verified"] is True


def test_run_downgrades_legacy_pass_contract(tmp_path):
    root, config_path = _fixture(tmp_path)
    output = root / "product-results.json"
    result = _run(
        ["--run", "--config", str(config_path), "--output", str(output), "--root", str(root)],
        env_extra={"AIQE_TESTED_COMMIT_SHA": SHA, "FAKE_TC_MODE": "legacy-pass"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["product_tc_pass"] == 0
    assert payload["summary"]["NOT_PROVEN"] == 10
    for item in payload["tests"]:
        assert item["status"] == "NOT_PROVEN"
        assert item["contract_errors"]
        assert item["claimed_status"] == "PASS"


def test_run_with_failed_runner_is_nonzero(tmp_path):
    root, config_path = _fixture(tmp_path)
    output = root / "product-results.json"
    result = _run(
        ["--run", "--config", str(config_path), "--output", str(output), "--root", str(root)],
        env_extra={"AIQE_TESTED_COMMIT_SHA": SHA, "FAKE_TC_MODE": "fail"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["product_tc_pass"] == 0
    assert payload["summary"]["FAIL"] == 10


def test_run_missing_runner_result_is_not_proven(tmp_path):
    root, config_path = _fixture(tmp_path)
    output = root / "product-results.json"
    result = _run(
        ["--run", "--config", str(config_path), "--output", str(output), "--root", str(root)],
        env_extra={"AIQE_TESTED_COMMIT_SHA": SHA, "FAKE_TC_MODE": "no-result"},
    )
    assert result.returncode == 2, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["NOT_PROVEN"] == 10
    assert payload["summary"]["product_tc_pass"] == 0


def test_config_rejects_missing_tc(tmp_path):
    config = copy.deepcopy(MODULE.load_config(CONFIG))
    config["test_cases"] = [
        case for case in config["test_cases"] if case["tc_id"] != "TC-AIQE-010"
    ]
    errors = MODULE.validate_config(config)
    assert any("TC-AIQE-010" in item for item in errors)


def test_config_rejects_unexplained_null_runner(tmp_path):
    config = copy.deepcopy(MODULE.load_config(CONFIG))
    case = config["test_cases"][0]
    case.pop("owner", None)
    case.pop("unblock_action", None)
    case["blocked_status"] = "PASS"
    errors = MODULE.validate_config(config)
    assert any("owner" in item for item in errors)
    assert any("unblock_action" in item for item in errors)
    assert any("blocked_status" in item for item in errors)
