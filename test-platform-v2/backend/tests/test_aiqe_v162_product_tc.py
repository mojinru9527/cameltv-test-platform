"""V1.6.2 FIX-002 / FIX-003：产品 TC 统一 Runner 框架与基线映射测试。

覆盖：
- 配置 schema 2.0 合同（10 条、必需字段、空 runner 的显式 BLOCKED 元数据）；
- ``--check-config`` 只输出 CONFIG_VALID、不出现 PASS；
- ``--plan`` 列出 10 条且不执行；
- 无环境 ``--run`` 输出 BLOCKED/NOT_PROVEN 且非零退出；
- ``verify_product_tc_results.py`` 拒绝伪造 PASS / artifact hash / 旧 SHA / local 环境；
- 正向 fixture（真实临时 artifact + sha256）能通过验证，证明校验器不是永远失败；
- 提交的 product-results.json 是机器生成的 BLOCKED，不是静态通过摘要。
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts/aiqe"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from per_tc.runner_contract import (  # noqa: E402
    ARTIFACT_KIND,
    RUNNER_TYPES,
    artifact_entry,
    assertion_result,
    execution_block,
    pass_record,
    summarize,
)

RUN_SCRIPT = SCRIPTS_DIR / "run_product_tc.py"
VERIFY_SCRIPT = SCRIPTS_DIR / "verify_product_tc_results.py"
CONFIG = REPO_ROOT / "docs/aiqe/v1.6/e2e/product-tc-config.yaml"
RESULTS = REPO_ROOT / "docs/aiqe/v1.6/e2e/product-results.json"
STUB_RUNNER = SCRIPTS_DIR / "per_tc/product_tc_stub_runner.py"
TC_IDS = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))
BASELINE = "v1.6.2-hardening"
ENVIRONMENT = "isolated-test"
SHA = "a" * 40
FORBIDDEN_RUNNER_MARKERS = ("futurewayu", "production", "scripts/qa", "aiqe_test5", "test5_")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUN_MODULE = _load(RUN_SCRIPT, "run_product_tc_v162")
VERIFY_MODULE = _load(VERIFY_SCRIPT, "verify_product_tc_results_v162")


def _run(
    script: Path, args: list[str], *, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=300,
    )


def _write_config(root: Path) -> dict:
    runner_path = root / "scripts/fake_runner.py"
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text("raise SystemExit(0)\n", encoding="utf-8")
    cases = []
    for tc_id in TC_IDS:
        cases.append(
            {
                "tc_id": tc_id,
                "title": f"{tc_id} fixture",
                "spec_ref": "merged-spec §20",
                "baseline_version": BASELINE,
                "required_environment": ENVIRONMENT,
                "required_assertions": ["assert.ok"],
                "required_artifacts": ["trace"],
                "timeout_seconds": 120,
                "runner": {
                    "type": "external_runner",
                    "entrypoint": "scripts/fake_runner.py",
                    "version": "1.0.0",
                },
            }
        )
    config = {
        "schema_version": "2.0",
        "baseline_version": BASELINE,
        "environment": ENVIRONMENT,
        "test_cases": cases,
    }
    (root / "config.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return config


def _compliant_results(root: Path, config: dict, *, commit: str = SHA) -> dict:
    """模拟合规假 runner 的写回结果：真实临时 artifact + sha256 + 完整 execution。"""
    tests = []
    for case in config["test_cases"]:
        tc_id = case["tc_id"]
        artifact_rel = f"artifacts/{tc_id}.txt"
        artifact_path = root / artifact_rel
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(f"{tc_id} trace {commit}\n", encoding="utf-8")
        started = datetime.now(UTC) - timedelta(seconds=2)
        finished = datetime.now(UTC)
        execution = execution_block(
            run_id=f"run-{tc_id}",
            job_id=f"job-{tc_id}",
            tested_commit_sha=commit,
            environment=config["environment"],
            started_at=started,
            finished_at=finished,
        )
        tests.append(
            pass_record(
                tc_id,
                runner={
                    "name": "fake_runner",
                    "type": "external_runner",
                    "version": "1.0.0",
                    "entrypoint": "scripts/fake_runner.py",
                },
                execution=execution,
                assertions=[assertion_result("assert.ok", evidence_ref=artifact_rel)],
                artifacts=[artifact_entry("trace", "trace", artifact_rel, root=root)],
                baseline_version=config["baseline_version"],
                root=root,
            )
        )
    return {
        "schema_version": "2.0",
        "artifact_kind": ARTIFACT_KIND,
        "baseline_version": config["baseline_version"],
        "commit_sha": commit,
        "environment": config["environment"],
        "generated_at": datetime.now(UTC).isoformat(),
        "verification": {
            "verified": False,
            "verified_commit_sha": None,
            "verified_at": None,
            "verifier": {"name": "verify_product_tc_results", "version": "1.0.0"},
            "errors": ["fixture 尚未验证"],
            "results_sha256": None,
        },
        "tests": tests,
        "summary": summarize(tests),
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, dict, Path]:
    root = tmp_path
    config = _write_config(root)
    results = _compliant_results(root, config)
    results_path = root / "product-results.json"
    _write_json(results_path, results)
    return root, config, results_path


def _verify(
    root: Path,
    results_path: Path,
    *,
    config_path: Path | None = None,
    expected: str = SHA,
    extra: list[str] | None = None,
):
    return _run(
        VERIFY_SCRIPT,
        [
            "--config",
            str(config_path or root / "config.yaml"),
            "--results",
            str(results_path),
            "--root",
            str(root),
            "--expected-commit",
            expected,
            *(extra or []),
        ],
    )


def _blocked_results(tmp_path: Path) -> tuple[Path, dict]:
    output = tmp_path / "blocked-results.json"
    result = _run(RUN_SCRIPT, ["--run", "--output", str(output)])
    assert result.returncode == 2, result.stdout + result.stderr
    return output, json.loads(output.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 配置合同
# --------------------------------------------------------------------------- #
def test_config_is_schema_2_0_with_required_case_contract():
    config = RUN_MODULE.load_config(CONFIG)
    assert config["schema_version"] == "2.0"
    assert config["baseline_version"] == BASELINE
    assert config["environment"] == ENVIRONMENT
    assert RUN_MODULE.validate_config(config) == []
    assert [case["tc_id"] for case in config["test_cases"]] == list(TC_IDS)
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
        assert case["baseline_version"] == config["baseline_version"]


def test_config_does_not_register_external_production_manual_scripts():
    config = RUN_MODULE.load_config(CONFIG)
    for case in config["test_cases"]:
        runner = case.get("runner")
        if runner is None:
            continue
        entrypoint = str(runner.get("entrypoint") if isinstance(runner, dict) else runner[0]).lower()
        for marker in FORBIDDEN_RUNNER_MARKERS:
            assert marker not in entrypoint, f"{case['tc_id']} 注册了外部生产/手工脚本: {entrypoint}"
        if isinstance(runner, dict):
            assert runner.get("type") in RUNNER_TYPES


def test_check_config_output_contains_only_config_valid():
    result = _run(RUN_SCRIPT, ["--check-config"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CONFIG_VALID" in result.stdout
    assert "PASS" not in result.stdout.upper()
    assert "product_tc_pass" not in result.stdout


def test_plan_lists_ten_cases_without_executing(tmp_path):
    output = tmp_path / "not-written.json"
    result = _run(RUN_SCRIPT, ["--plan", "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert [case["tc_id"] for case in payload["cases"]] == list(TC_IDS)
    assert payload["summary"]["total"] == 10
    assert all(case["planned_status"] == "BLOCKED" for case in payload["cases"])
    assert not output.exists()


def test_run_without_environment_outputs_blocked_and_nonzero(tmp_path):
    output, payload = _blocked_results(tmp_path)
    assert payload["baseline_version"] == BASELINE
    assert payload["environment"] == ENVIRONMENT
    assert len(payload["commit_sha"]) == 40
    assert payload["summary"]["product_tc_pass"] == 0
    assert payload["summary"]["BLOCKED"] == 10
    assert payload["verification"]["verified"] is False
    assert all(item["status"] == "BLOCKED" for item in payload["tests"])
    assert all(item["blocked_reason"] for item in payload["tests"])
    assert all(item["execution"] is None for item in payload["tests"])


# --------------------------------------------------------------------------- #
# 验证器：反伪造
# --------------------------------------------------------------------------- #
def test_verify_rejects_forged_blocked_to_pass(tmp_path):
    output, payload = _blocked_results(tmp_path)
    record = payload["tests"][0]
    record["status"] = "PASS"
    record["blocked_reason"] = None
    payload["tests"][0] = record
    payload["summary"] = summarize(payload["tests"])
    _write_json(output, payload)
    result = _verify(
        REPO_ROOT, output, config_path=CONFIG, expected=payload["commit_sha"]
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "配置未注册可执行 runner" in result.stdout or "PASS" in result.stdout
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["verification"]["verified"] is False
    assert written["verification"]["errors"]


def test_verify_rejects_artifact_hash_mismatch(tmp_path):
    root, _, results_path = _fixture(tmp_path)
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    payload["tests"][0]["artifacts"][0]["sha256"] = "0" * 64
    _write_json(results_path, payload)
    result = _verify(root, results_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "hash 不匹配" in result.stdout


def test_verify_rejects_reused_old_sha(tmp_path):
    root, _, results_path = _fixture(tmp_path)
    result = _verify(root, results_path, expected="b" * 40)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "commit_sha" in result.stdout or "SHA" in result.stdout


def test_verify_rejects_local_environment(tmp_path):
    root, _, results_path = _fixture(tmp_path)
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    payload["environment"] = "local"
    for record in payload["tests"]:
        record["execution"]["environment"] = "local"
    _write_json(results_path, payload)
    result = _verify(root, results_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "environment" in result.stdout


def test_verify_rejects_missing_execution_provenance(tmp_path):
    root, _, results_path = _fixture(tmp_path)
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    payload["tests"][0]["execution"]["run_id"] = ""
    payload["tests"][0]["execution"]["job_id"] = ""
    _write_json(results_path, payload)
    result = _verify(root, results_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "run_id" in result.stdout and "job_id" in result.stdout


def test_verify_rejects_pass_without_assertion_evidence(tmp_path):
    root, _, results_path = _fixture(tmp_path)
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    payload["tests"][0]["assertions"] = []
    _write_json(results_path, payload)
    result = _verify(root, results_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "业务断言" in result.stdout


def test_verify_detects_manual_edit_after_verification(tmp_path):
    root, _, results_path = _fixture(tmp_path)
    first = _verify(root, results_path)
    assert first.returncode == 0, first.stdout + first.stderr
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["verification"]["verified"] is True
    payload["tests"][0]["assertions"][0]["status"] = "FAIL"
    _write_json(results_path, payload)
    second = _verify(root, results_path)
    assert second.returncode == 1, second.stdout + second.stderr
    assert "验证后被修改" in second.stdout


# --------------------------------------------------------------------------- #
# 验证器：正向（证明校验器不是永远失败）
# --------------------------------------------------------------------------- #
def test_verify_accepts_compliant_fixture(tmp_path):
    root, _, results_path = _fixture(tmp_path)
    result = _verify(root, results_path, extra=["--require-pass"])
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["verification"]["verified"] is True
    assert payload["verification"]["verified_commit_sha"] == SHA
    assert payload["verification"]["errors"] == []
    assert payload["verification"]["results_sha256"]
    for record in payload["tests"]:
        for artifact in record["artifacts"]:
            path = root / artifact["path"]
            assert path.is_file()
            assert artifact["sha256"]


def test_verify_require_pass_rejects_blocked_results(tmp_path):
    output, payload = _blocked_results(tmp_path)
    result = _verify(
        REPO_ROOT,
        output,
        config_path=CONFIG,
        expected=payload["commit_sha"],
        extra=["--require-pass"],
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "require-pass" in result.stdout + result.stderr


def test_stub_runner_only_outputs_blocked(tmp_path):
    result_path = tmp_path / "stub-probe.json"
    result = _run(
        STUB_RUNNER,
        ["--tc", "TC-AIQE-001", "--result-path", str(result_path)],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED"
    assert payload["execution"] is None
    assert "run_id" not in payload
    assert payload["blocked_reason"]


def test_runner_types_match_release_verdict_validator():
    spec = importlib.util.spec_from_file_location(
        "product_tc_validator_v162", SCRIPTS_DIR / "validators/product_tc.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.RUNNER_TYPES == RUNNER_TYPES


# --------------------------------------------------------------------------- #
# 仓库内提交的结果文件必须是机器生成的 BLOCKED
# --------------------------------------------------------------------------- #
def test_committed_product_results_are_machine_blocked():
    payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert payload["artifact_kind"] == ARTIFACT_KIND
    assert payload["baseline_version"] == BASELINE
    assert payload["environment"] == ENVIRONMENT
    assert len(payload["commit_sha"]) == 40
    assert payload["summary"]["product_tc_pass"] == 0
    assert payload["summary"]["ga_ready"] is False
    assert [item["tc_id"] for item in payload["tests"]] == list(TC_IDS)
    assert all(item["status"] == "BLOCKED" for item in payload["tests"])
    assert not any(item["status"] == "PASS" for item in payload["tests"])
    assert payload["verification"]["verified"] is True
    assert payload["verification"]["product_tc_pass"] == 0
    assert payload["verification"]["product_tc_total"] == 10


def test_committed_product_results_pass_verification_but_not_require_pass():
    payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    expected = payload["commit_sha"]
    result = _run(
        VERIFY_SCRIPT,
        [
            "--config",
            str(CONFIG),
            "--results",
            str(RESULTS),
            "--root",
            str(REPO_ROOT),
            "--expected-commit",
            expected,
            "--no-write",
        ],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["verified"] is True
    assert report["status_counts"]["BLOCKED"] == 10
    require_pass = _run(
        VERIFY_SCRIPT,
        [
            "--config",
            str(CONFIG),
            "--results",
            str(RESULTS),
            "--root",
            str(REPO_ROOT),
            "--expected-commit",
            expected,
            "--require-pass",
            "--no-write",
        ],
    )
    assert require_pass.returncode == 1, require_pass.stdout + require_pass.stderr
