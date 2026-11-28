"""FIX-001 RV-001..RV-012：Release Verdict Gate E 假绿反向测试。

每个用例都从完整 PASS fixture 出发，只破坏一个事实，断言 Gate E 必须非 PASS。
RV-012 保留完整 fixture，证明门禁不是“永远失败”。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/release_verdict.py"
SHA = "a" * 40
NOW_START = "2026-11-28T00:00:00Z"
NOW_END = "2026-11-28T00:00:01Z"
DIGEST = "sha256:" + "b" * 64
SNAPSHOT = "c" * 64


def _load_release_verdict():
    spec = importlib.util.spec_from_file_location("release_verdict_v162", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_release_verdict()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")


def _artifact(root: Path, rel: str, content: str) -> tuple[str, str]:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return rel, hashlib.sha256(content.encode("utf-8")).hexdigest()


def _config(root: Path) -> dict:
    runner_path = root / "scripts/aiqe/tc_runner.py"
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text("raise SystemExit(0)\n", encoding="utf-8")
    cases = []
    for index in range(1, 11):
        cases.append(
            {
                "tc_id": f"TC-AIQE-{index:03d}",
                "title": f"TC {index}",
                "spec_ref": "merged-spec §20",
                "baseline_version": "v1.6.2",
                "runner": {
                    "type": "api_worker_e2e",
                    "entrypoint": "scripts/aiqe/tc_runner.py",
                    "version": "1.0.0",
                },
                "required_environment": "ci-test",
                "required_assertions": ["assert.ok"],
                "required_artifacts": ["trace"],
                "timeout_seconds": 900,
            }
        )
    return {
        "schema_version": "2.0",
        "baseline_version": "v1.6.2",
        "environment": "ci-test",
        "test_cases": cases,
    }


def _results(root: Path, config: dict) -> dict:
    tests = []
    for case in config["test_cases"]:
        rel, digest = _artifact(root, f"docs/aiqe/v1.6/evidence/product/{case['tc_id']}/trace.txt", case["tc_id"])
        tests.append(
            {
                "tc_id": case["tc_id"],
                "status": "PASS",
                "runner": dict(case["runner"]),
                "execution": {
                    "run_id": f"run-{case['tc_id']}",
                    "job_id": f"job-{case['tc_id']}",
                    "tested_commit_sha": SHA,
                    "environment": "ci-test",
                    "started_at": NOW_START,
                    "finished_at": NOW_END,
                    "duration_ms": 1000,
                },
                "assertions": [
                    {
                        "assertion_id": "assert.ok",
                        "status": "PASS",
                        "evidence_ref": rel,
                    }
                ],
                "artifacts": [
                    {
                        "artifact_id": "trace",
                        "kind": "trace",
                        "path": rel,
                        "sha256": digest,
                    }
                ],
                "blocked_reason": "",
            }
        )
    return {
        "schema_version": "2.0",
        "artifact_kind": "product-tc-results",
        "baseline_version": "v1.6.2",
        "commit_sha": SHA,
        "environment": "ci-test",
        "generated_at": NOW_END,
        "verification": {
            "verified": True,
            "verified_commit_sha": SHA,
            "verified_at": NOW_END,
            "verifier": {"name": "verify_product_tc_results", "version": "1.0"},
            "errors": [],
        },
        "tests": tests,
        "summary": {
            "product_tc_pass": 10,
            "product_tc_total": 10,
            "PASS": 10,
            "FAIL": 0,
            "BLOCKED": 0,
            "NOT_RUN": 0,
        },
    }


def _runtime() -> dict:
    tests = []
    for index in range(1, 11):
        tests.append(
            {
                "tc_id": f"TC-PLATFORM-{index:03d}",
                "status": "PASS",
                "run_id": f"prun-{index}",
                "project_id": 1,
                "workflow_snapshot_hash": SNAPSHOT,
                "job_ids": [index],
                "node_run_ids": [f"node-{index}"],
                "assertion_ids": [f"assert-{index}"],
                "artifact_refs": [f"artifact-{index}"],
                "driver_image_digest": DIGEST,
                "duration_ms": 1000,
                "started_at": NOW_START,
                "finished_at": NOW_END,
            }
        )
    return {
        "schema_version": "2.0",
        "commit_sha": SHA,
        "ci_run_id": "123456",
        "environment": "ci-test",
        "generated_at": NOW_END,
        "tests": tests,
        "summary": {
            "PASS": 10,
            "FAIL": 0,
            "BLOCKED": 0,
            "NOT_RUN": 0,
            "total": 10,
            "executed": 10,
            "ga_ready": True,
        },
    }


def _platform() -> dict:
    tests = []
    for index in range(1, 11):
        tests.append(
            {
                "tc_id": f"TC-PLATFORM-{index:03d}",
                "status": "PASS",
                "run_id": f"prun-{index}",
                "project_id": 1,
                "workflow_snapshot_hash": SNAPSHOT,
                "job_ids": [index],
                "node_run_ids": [f"node-{index}"],
                "assertion_ids": [f"assert-{index}"],
                "artifact_refs": [f"artifact-{index}"],
                "driver_image_digest": DIGEST,
                "duration_ms": 1000,
                "run_status": "COMPLETED",
                "run_outcome": "PASS",
            }
        )
    return {
        "schema_version": "2.0",
        "commit_sha": SHA,
        "ci_run": "123456",
        "environment": "ci-test",
        "generated_at": NOW_END,
        "tests": tests,
    }


def _entries() -> list[dict]:
    return [
        {
            "id": f"TC-AIQE-{index:03d}",
            "acceptance": {"status": "REVIEWED"},
            "e2e": {"product": {"status": "PASS"}},
        }
        for index in range(1, 11)
    ]


def _fixture(tmp_path: Path) -> dict:
    docs = tmp_path / "docs/aiqe/v1.6"
    (tmp_path / "scripts/aiqe").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts/aiqe/check_traceability.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    config = _config(tmp_path)
    results = _results(tmp_path, config)
    runtime = _runtime()
    platform = _platform()
    _write_yaml(docs / "e2e/product-tc-config.yaml", config)
    _write_json(docs / "e2e/product-results.json", results)
    _write_json(docs / "evidence/evidence-index.json", runtime)
    _write_json(docs / "e2e/platform-results.json", platform)
    (docs / "traceability").mkdir(parents=True, exist_ok=True)
    _write_yaml(
        docs / "traceability/requirements.yaml",
        {"schema_version": "2.0", "release": "aiqe-v1.6.2", "baseline": {"release_commit": SHA}, "requirements": []},
    )
    return {
        "root": tmp_path,
        "docs": docs,
        "config": config,
        "results": results,
        "runtime": runtime,
        "platform": platform,
    }


def _evaluate(fixture: dict):
    return MODULE.evaluate_gate_e(
        _entries(),
        root=fixture["root"],
        expected_commit=SHA,
        expected_environment="ci-test",
    )[0]


def _assert_blocked(check, label: str) -> None:
    assert check.status != "PASS", f"{label}: Gate E 不应 PASS: {check.as_dict()}"


def test_rv_012_complete_fixture_passes(tmp_path):
    check = _evaluate(_fixture(tmp_path))
    assert check.status == "PASS", check.as_dict()


def test_rv_001_runtime_ga_ready_false_blocks_even_with_10_of_10(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["runtime"]["summary"]["ga_ready"] = False
    _write_json(fixture["docs"] / "evidence/evidence-index.json", fixture["runtime"])
    _assert_blocked(_evaluate(fixture), "RV-001")


def test_rv_002_null_runners_are_not_proven(tmp_path):
    fixture = _fixture(tmp_path)
    for case in fixture["config"]["test_cases"]:
        case["runner"] = None
    _write_yaml(fixture["docs"] / "e2e/product-tc-config.yaml", fixture["config"])
    _assert_blocked(_evaluate(fixture), "RV-002")


def test_rv_003_one_not_run_is_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["results"]["tests"][0]["status"] = "NOT_RUN"
    fixture["results"]["tests"][0]["blocked_reason"] = "fixture"
    _write_json(fixture["docs"] / "e2e/product-results.json", fixture["results"])
    _assert_blocked(_evaluate(fixture), "RV-003")


def test_rv_004_semi_automatic_is_partial_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["results"]["tests"][0]["status"] = "SEMI_AUTOMATIC"
    _write_json(fixture["docs"] / "e2e/product-results.json", fixture["results"])
    _assert_blocked(_evaluate(fixture), "RV-004")


def test_rv_005_missing_run_id_is_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["results"]["tests"][0]["execution"]["run_id"] = ""
    _write_json(fixture["docs"] / "e2e/product-results.json", fixture["results"])
    _assert_blocked(_evaluate(fixture), "RV-005")


def test_rv_006_missing_assertion_is_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["results"]["tests"][0]["assertions"] = []
    _write_json(fixture["docs"] / "e2e/product-results.json", fixture["results"])
    _assert_blocked(_evaluate(fixture), "RV-006")


def test_rv_007_artifact_hash_mismatch_is_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["results"]["tests"][0]["artifacts"][0]["sha256"] = "0" * 64
    _write_json(fixture["docs"] / "e2e/product-results.json", fixture["results"])
    _assert_blocked(_evaluate(fixture), "RV-007")


def test_rv_008_sha_mismatch_is_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["results"]["tests"][0]["execution"]["tested_commit_sha"] = "d" * 40
    _write_json(fixture["docs"] / "e2e/product-results.json", fixture["results"])
    _assert_blocked(_evaluate(fixture), "RV-008")


def test_rv_009_local_environment_is_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["runtime"]["environment"] = "local"
    _write_json(fixture["docs"] / "evidence/evidence-index.json", fixture["runtime"])
    _assert_blocked(_evaluate(fixture), "RV-009")


def test_rv_010_missing_driver_digest_is_not_pass(tmp_path):
    fixture = _fixture(tmp_path)
    for item in fixture["runtime"]["tests"]:
        item["driver_image_digest"] = ""
    _write_json(fixture["docs"] / "evidence/evidence-index.json", fixture["runtime"])
    _assert_blocked(_evaluate(fixture), "RV-010")


def test_rv_011_forged_ga_ready_with_internal_blocked_is_rejected(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["runtime"]["summary"]["ga_ready"] = True
    fixture["runtime"]["tests"][0]["status"] = "BLOCKED"
    fixture["runtime"]["tests"][0]["blocked_reason"] = "fixture"
    _write_json(fixture["docs"] / "evidence/evidence-index.json", fixture["runtime"])
    _assert_blocked(_evaluate(fixture), "RV-011")


def test_cli_require_ga_nonzero_for_fake_green(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["runtime"]["summary"]["ga_ready"] = False
    _write_json(fixture["docs"] / "evidence/evidence-index.json", fixture["runtime"])
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--require-ga"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Gate E" in result.stdout
