"""V16-023 验收：evidence-index 生成器必须拒绝缺失追溯链/重复 TC/伪 PASS。

FIX-011 扩展（2026-11-28）：
- 输入 artifact 的 tested SHA 是事实源，Builder 不得覆盖；与 CLI 冲突即失败；
- 新增 source/runtime/workflow/artifacts/verification 结构；
- environment 缺失/本地环境为 NOT_PROVEN；duration 由起止时间计算，冲突保留原始值；
- container Runner 必须有 immutable image digest。
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "aiqe" / "build_evidence_index.py"
DIGEST = "sha256:" + "b" * 64
STARTED_AT = "2026-11-28T00:00:00Z"
FINISHED_AT = "2026-11-28T00:00:01.200Z"


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
        "duration_ms": 1200,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
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
        runtime_type=kwargs.pop("runtime_type", "container"),
        driver_image_digest=kwargs.pop("driver_image_digest", DIGEST),
        started_at=kwargs.pop("started_at", "2026-11-28T00:00:00Z"),
        finished_at=kwargs.pop("finished_at", "2026-11-28T00:00:20Z"),
        workflow_attempt=kwargs.pop("workflow_attempt", "1"),
        workflow_job_id=kwargs.pop("workflow_job_id", "job-1"),
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
    ok = subprocess.run(
        base, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
    )
    assert ok.returncode == 0, ok.stderr
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["ci_run_id"] == "999"
    assert data["summary"]["BLOCKED"] == 1

    strict = subprocess.run(
        base + ["--fail-on-blocked"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert strict.returncode != 0
    assert "BLOCKED" in strict.stderr


# ---------------------------------------------------------------------------
# FIX-011：原始 provenance 不可被 Builder 覆盖
# ---------------------------------------------------------------------------
def test_input_artifact_tested_sha_is_preserved():
    declared = "1" * 40
    index = _build(
        [_record(1)],
        commit_sha="",
        input_payload={"commit_sha": declared, "tests": []},
    )
    assert index["commit_sha"] == declared
    assert index["source"]["tested_commit_sha"] == declared
    assert index["source"]["tested_commit_sha_origin"] == "artifact"


def test_conflicting_commit_flag_is_rejected():
    declared = "1" * 40
    with pytest.raises(MODULE.EvidenceError) as excinfo:
        _build(
            [_record(1)],
            commit_sha="2" * 40,
            input_payload={"tested_commit_sha": declared, "tests": []},
        )
    assert "tested_commit_sha" in str(excinfo.value)


def test_sha_side_channels_are_recorded_separately():
    index = _build(
        [_record(1)],
        pr_head_sha="3" * 40,
        merge_commit_sha="4" * 40,
        release_target_sha="5" * 40,
    )
    source = index["source"]
    assert source["tested_commit_sha"] == "c" * 40
    assert source["pr_head_sha"] == "3" * 40
    assert source["merge_commit_sha"] == "4" * 40
    assert source["release_target_sha"] == "5" * 40
    assert index["workflow"] == {"run_id": "123456", "attempt": 1, "job_id": "job-1"}


def test_local_environment_is_not_proven():
    index = _build([_record(1)], environment="local")
    assert index["verification"]["provenance_valid"] is False
    assert any("本地" in item for item in index["verification"]["errors"])
    assert index["summary"]["ga_ready"] is False
    assert index["runtime"]["environment"] == "local"


def test_local_prefixed_environment_is_not_proven():
    index = _build([_record(1)], environment="local-20261124")
    assert index["verification"]["provenance_valid"] is False
    assert index["summary"]["ga_ready"] is False


def test_environment_conflict_keeps_artifact_value():
    index = _build(
        [_record(1)],
        environment="ci",
        input_payload={"environment": "local-20261124", "commit_sha": "c" * 40},
    )
    assert index["runtime"]["environment"] == "local-20261124"
    assert index["environment"] == "local-20261124"
    assert index["verification"]["provenance_valid"] is False
    assert any("environment 冲突" in item for item in index["verification"]["errors"])


def test_duration_is_computed_from_timestamps_when_missing():
    index = _build([_record(1)])
    assert index["runtime"]["duration_ms"] == 20000
    assert index["runtime"]["duration_source"] == "computed"
    assert index["verification"]["provenance_valid"] is True


def test_duration_conflict_keeps_original_and_records_error():
    index = _build(
        [_record(1)],
        input_payload={
            "commit_sha": "c" * 40,
            "runtime": {
                "duration_ms": 0,
                "started_at": "2026-11-28T00:00:00Z",
                "finished_at": "2026-11-28T00:00:02Z",
            },
        },
    )
    assert index["runtime"]["duration_ms"] == 0
    assert index["runtime"]["computed_duration_ms"] == 2000
    assert any("duration_ms=0" in item and "冲突" in item for item in index["verification"]["errors"])
    assert index["verification"]["provenance_valid"] is False


def test_container_runner_requires_immutable_digest():
    index = _build([_record(1, driver_image_digest="")], driver_image_digest="")
    assert index["verification"]["provenance_valid"] is False
    assert any("driver_image_digest" in item for item in index["verification"]["errors"])
    tag_only = _build([_record(1, driver_image_digest="sha256:tag")], driver_image_digest="sha256:tag")
    assert tag_only["verification"]["provenance_valid"] is False


def test_artifacts_manifest_records_name_path_hash_and_job():
    index = _build(
        [
            _record(
                1,
                artifacts=[
                    {
                        "name": "trace.zip",
                        "path": "work-logs/evidence/trace.zip",
                        "sha256": "e" * 64,
                        "job_id": 7,
                    }
                ],
            )
        ]
    )
    artifact = index["artifacts"][0]
    assert artifact["name"] == "trace.zip"
    assert artifact["path"] == "work-logs/evidence/trace.zip"
    assert artifact["sha256"] == "e" * 64
    assert artifact["job_id"] == 7


def test_cli_records_full_provenance(tmp_path: Path):
    input_path = tmp_path / "results.json"
    output_path = tmp_path / "evidence-index.json"
    declared = "a" * 40
    input_path.write_text(
        json.dumps({"commit_sha": declared, "tests": [_record(1)]}), encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(input_path),
            "--tested-commit-sha",
            declared,
            "--pr-head-sha",
            "b" * 40,
            "--merge-commit-sha",
            "c" * 40,
            "--ci-run",
            "424242",
            "--workflow-attempt",
            "2",
            "--job-id",
            "job-42",
            "--environment",
            "ci-test",
            "--runtime-type",
            "container",
            "--driver-image-digest",
            DIGEST,
            "--started-at",
            "2026-11-28T00:00:00Z",
            "--finished-at",
            "2026-11-28T00:00:21Z",
            "--output",
            str(output_path),
            "--require-tcs",
            "1",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    index = json.loads(output_path.read_text(encoding="utf-8"))
    assert index["source"]["tested_commit_sha"] == declared
    assert index["source"]["pr_head_sha"] == "b" * 40
    assert index["source"]["merge_commit_sha"] == "c" * 40
    assert index["runtime"]["environment"] == "ci-test"
    assert index["runtime"]["duration_ms"] == 21000
    assert index["workflow"]["run_id"] == "424242"
    assert index["workflow"]["attempt"] == 2
    assert index["workflow"]["job_id"] == "job-42"
    assert index["artifacts"][0]["role"] == "source"
    assert index["artifacts"][0]["sha256"] == MODULE._sha256_bytes(input_path.read_bytes())
    assert index["verification"]["provenance_valid"] is True


def test_cli_rejects_flag_that_would_override_tested_sha(tmp_path: Path):
    input_path = tmp_path / "results.json"
    output_path = tmp_path / "evidence-index.json"
    input_path.write_text(
        json.dumps({"commit_sha": "a" * 40, "tests": [_record(1)]}), encoding="utf-8"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(input_path),
            "--commit-sha",
            "b" * 40,
            "--ci-run",
            "1",
            "--environment",
            "ci",
            "--output",
            str(output_path),
            "--require-tcs",
            "1",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode != 0
    assert "tested_commit_sha" in result.stderr
    assert not output_path.exists()
