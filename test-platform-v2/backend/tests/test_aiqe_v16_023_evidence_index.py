"""V16-023 验收：evidence-index 生成器必须拒绝缺失追溯链/重复 TC/伪 PASS。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "aiqe" / "build_evidence_index.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_evidence_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _record(index: int, **overrides):
    data = {
        "tc_id": f"TC-AIQE-{index:03d}",
        "status": "PASS",
        "run_id": f"run-{index}",
        "project_id": 1,
        "workflow_snapshot_hash": "a" * 64,
        "job_ids": [index],
        "node_run_ids": [f"node-{index}"],
        "assertion_ids": [f"assertion-{index}"],
        "artifact_refs": [f"artifact:{index}"],
        "driver_image_digest": "sha256:" + "b" * 64,
    }
    data.update(overrides)
    return data


def _build(records, **kwargs):
    module = MODULE
    return module.build_index(
        tests=records,
        commit_sha=kwargs.pop("commit_sha", "c" * 40),
        ci_run_id=kwargs.pop("ci_run_id", "123456"),
        environment=kwargs.pop("environment", "ci"),
        **kwargs,
    )


def test_valid_ten_tcs_builds_ga_ready_index():
    index = _build([_record(i) for i in range(1, 11)])
    assert index["summary"]["total"] == 10
    assert index["summary"]["pass_rate_excluding_blocked"] == 1.0
    assert index["summary"]["ga_ready"] is True
    assert index["commit_sha"] == "c" * 40
    assert index["tests"][0]["job_ids"] == [1]


def test_pass_without_artifact_is_rejected():
    with pytest.raises(MODULE.EvidenceError):
        _build([_record(1, artifact_refs=[])])


def test_pass_without_job_is_rejected():
    with pytest.raises(MODULE.EvidenceError):
        _build([_record(1, job_ids=[])])


def test_duplicate_tc_rejected():
    with pytest.raises(MODULE.EvidenceError):
        _build([_record(1), _record(1)])


def test_invalid_commit_sha_rejected():
    with pytest.raises(MODULE.EvidenceError):
        _build([_record(1)], commit_sha="abc1234")


def test_blocked_requires_reason_and_is_excluded_from_pass_rate():
    with pytest.raises(MODULE.EvidenceError):
        _build([_record(1, status="BLOCKED", blocked_reason="")])
    index = _build(
        [
            _record(1),
            _record(2, status="BLOCKED", blocked_reason="环境无设备"),
            _record(3, status="NOT_RUN", blocked_reason="未执行"),
        ],
        require_tcs=3,
    )
    assert index["summary"]["PASS"] == 1
    assert index["summary"]["BLOCKED"] == 1
    assert index["summary"]["NOT_RUN"] == 1
    assert index["summary"]["pass_rate_excluding_blocked"] == 1.0
    assert index["summary"]["ga_ready"] is False


def test_require_tcs_enforced():
    with pytest.raises(MODULE.EvidenceError):
        _build([_record(1)], require_tcs=10)


def test_cli_writes_index_and_fails_on_blocked(tmp_path: Path):
    input_path = tmp_path / "results.json"
    output_path = tmp_path / "evidence-index.json"
    input_path.write_text(
        json.dumps({"tests": [_record(1), _record(2, status="BLOCKED", blocked_reason="x")]}),
        encoding="utf-8",
    )
    base = [
        sys.executable,
        str(SCRIPT),
        "--input",
        str(input_path),
        "--commit-sha",
        "d" * 40,
        "--ci-run",
        "999",
        "--environment",
        "staging",
        "--output",
        str(output_path),
        "--require-tcs",
        "2",
    ]
    ok = subprocess.run(base, capture_output=True, text=True, timeout=60)
    assert ok.returncode == 0, ok.stderr
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["ci_run_id"] == "999"
    assert data["summary"]["BLOCKED"] == 1

    strict = subprocess.run(base + ["--fail-on-blocked"], capture_output=True, text=True, timeout=60)
    assert strict.returncode != 0
    assert "BLOCKED" in strict.stderr
