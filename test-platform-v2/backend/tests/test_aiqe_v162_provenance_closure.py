"""FIX-011 / FIX-012 验收：provenance 不可覆盖 + 审计关闭语义验证。

FIX-011：
- Builder 必须保留输入 artifact 里的 tested SHA，冲突即失败；
- source/runtime/workflow/artifacts/verification 结构必须可被
  ``validators.provenance.validate_provenance`` 校验；
- environment 缺失/本地环境 = NOT_PROVEN；duration 冲突保留原始值。

FIX-012（手册 §13.5 六个场景）：
1. evidence 路径存在但内容不相关 → 不能 CLOSED；
2. TC Config runner null → V16-017 不能 CLOSED；
3. product results 10/10 但 runtime evidence 缺 8 项 → 不能 CLOSED；
4. evidence commit 不是当前 SHA → 不能 CLOSED；
5. matrix 与 product result 状态矛盾 → 报冲突且不能 CLOSED；
6. 证据完整且验证器通过 → 允许 CLOSED。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts/aiqe"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_evidence_index as BUILD  # noqa: E402
import check_audit_closure as CLOSURE  # noqa: E402
from validators import closure_rules  # noqa: E402
from validators.provenance import validate_provenance  # noqa: E402

SCRIPT = SCRIPTS / "check_audit_closure.py"
SHA = "a" * 40
OLD_SHA = "b" * 40
SNAPSHOT = "e" * 64
DIGEST = "sha256:" + "d" * 64
START = "2026-11-28T00:00:00Z"
END = "2026-11-28T00:00:10Z"
RUNNER = {
    "type": "api_worker_e2e",
    "version": "1.0.0",
    "entrypoint": "scripts/aiqe/tc_runner.py",
}


# ---------------------------------------------------------------------------
# 通用 fixture 工具
# ---------------------------------------------------------------------------
def _write(root: Path, rel: str, text: str) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return rel


def _write_json(root: Path, rel: str, payload: object) -> str:
    return _write(root, rel, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_yaml(root: Path, rel: str, payload: object) -> str:
    return _write(root, rel, yaml.safe_dump(payload, allow_unicode=True))


def _sha256(root: Path, rel: str) -> str:
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


def _closed_item(**overrides) -> dict:
    item = {
        "id": "P0-1",
        "issue_id": "P0-1",
        "requirement_id": "V16-017-R2",
        "title": "fixture closed item",
        "status": "CLOSED",
        "closure_rule_id": "GENERIC_FILE_EVIDENCE",
        "evidence": [],
        "rule_verdict": "PASS",
        "rule_checked_at": START,
        "verified_commit_sha": SHA,
        "verifier": {"name": "fixture", "version": "1.0.0", "ci_run_id": "12345"},
        "artifact_hashes": {},
        "verified_at": START,
        "review": {
            "reviewer_login": "reviewer-x",
            "review_id": "PRR_123",
            "reviewed_commit_sha": SHA,
        },
        "note": "fixture close",
    }
    item.update(overrides)
    return item


def _verify_closed(root: Path, item: dict, *, expected_commit: str = SHA):
    return CLOSURE.verify_closed({"items": [item]}, root=root, expected_commit=expected_commit)


# ---------------------------------------------------------------------------
# FIX-011：Builder 保留原始 provenance
# ---------------------------------------------------------------------------
def _record(index: int = 1, **overrides) -> dict:
    data = {
        "tc_id": f"TC-AIQE-{index:03d}",
        "status": "PASS",
        "run_id": f"run-{index}",
        "project_id": 1,
        "workflow_snapshot_hash": SNAPSHOT,
        "job_ids": [index],
        "node_run_ids": [f"node-{index}"],
        "assertion_ids": [f"assertion-{index}"],
        "artifact_refs": [f"artifact:{index}"],
        "driver_image_digest": DIGEST,
        "duration_ms": 10000,
        "started_at": START,
        "finished_at": END,
    }
    data.update(overrides)
    return data


def _build_index(**overrides) -> dict:
    kwargs = {
        "tests": [_record(1)],
        "commit_sha": SHA,
        "ci_run_id": "123456",
        "environment": "ci-test",
        "runtime_type": "container",
        "driver_image_digest": DIGEST,
        "started_at": START,
        "finished_at": END,
        "workflow_attempt": "1",
        "workflow_job_id": "job-1",
    }
    kwargs.update(overrides)
    return BUILD.build_index(**kwargs)


def test_builder_preserves_declared_tested_sha():
    index = _build_index(
        commit_sha="",
        input_payload={"tested_commit_sha": OLD_SHA, "tests": []},
    )
    assert index["source"]["tested_commit_sha"] == OLD_SHA
    assert index["commit_sha"] == OLD_SHA


def test_builder_rejects_override_of_tested_sha():
    try:
        _build_index(commit_sha="c" * 40, input_payload={"commit_sha": SHA, "tests": []})
    except BUILD.EvidenceError as exc:
        assert "tested_commit_sha" in str(exc)
    else:  # pragma: no cover - 必须抛错
        raise AssertionError("Builder 覆盖 tested SHA 必须失败")


def test_built_index_passes_provenance_structure_validation():
    index = _build_index(
        pr_head_sha="1" * 40,
        merge_commit_sha="2" * 40,
        release_target_sha="3" * 40,
    )
    assert index["source"]["pr_head_sha"] == "1" * 40
    assert index["source"]["merge_commit_sha"] == "2" * 40
    assert index["source"]["release_target_sha"] == "3" * 40
    check = validate_provenance(index, expected_tested_sha=SHA)
    assert check.status == "PASS", check.as_dict()


def test_local_environment_index_is_not_proven():
    index = _build_index(environment="local-20261124")
    assert index["verification"]["provenance_valid"] is False
    assert index["summary"]["ga_ready"] is False
    check = validate_provenance(index, expected_tested_sha=SHA)
    assert check.status != "PASS"


def test_duration_conflict_keeps_original_value():
    index = _build_index(
        input_payload={
            "commit_sha": SHA,
            "runtime": {"duration_ms": 0, "started_at": START, "finished_at": END},
        }
    )
    assert index["runtime"]["duration_ms"] == 0
    assert index["runtime"]["computed_duration_ms"] == 10000
    assert any("冲突" in item for item in index["verification"]["errors"])


def test_artifact_manifest_has_name_path_hash_and_job():
    index = _build_index(
        tests=[
            _record(
                1,
                artifacts=[
                    {
                        "name": "trace.zip",
                        "path": "work-logs/evidence/trace.zip",
                        "sha256": "f" * 64,
                        "job_id": 5,
                    }
                ],
            )
        ]
    )
    artifact = index["artifacts"][0]
    assert set(artifact) >= {"name", "path", "sha256", "job_id"}
    assert artifact["job_id"] == 5


# ---------------------------------------------------------------------------
# FIX-012 fixture：产品 TC / runtime index / 扫描 / 说明文档
# ---------------------------------------------------------------------------
def _product_fixture(
    root: Path,
    *,
    runners: str = "declared",
    results_pass: int = 10,
    matrix_status: dict[str, str] | None = None,
    traceable: bool = True,
) -> dict:
    _write(root, "scripts/aiqe/tc_runner.py", "raise SystemExit(0)\n")
    cases = []
    for index in range(1, 11):
        case = {
            "tc_id": f"TC-AIQE-{index:03d}",
            "title": f"TC {index}",
            "spec_ref": "merged-spec §20",
            "baseline_version": "v1.6.2",
            "required_assertions": ["assert.ok"],
            "required_artifacts": ["trace"],
        }
        if runners == "declared":
            case["runner"] = dict(RUNNER)
        else:
            case["runner"] = None
            case.update(
                {
                    "blocked_by": "needs env",
                    "owner": "qa-team",
                    "unblock_action": "provide env",
                    "blocked_status": "BLOCKED",
                }
            )
        cases.append(case)
    config = {
        "schema_version": "2.0",
        "baseline_version": "v1.6.2",
        "environment": "ci-test",
        "test_cases": cases,
    }
    tests = []
    for index in range(1, 11):
        tc_id = f"TC-AIQE-{index:03d}"
        artifact_rel = _write(
            root, f"docs/aiqe/v1.6/evidence/product/{tc_id}/trace.txt", tc_id
        )
        passed = index <= results_pass
        record = {
            "tc_id": tc_id,
            "status": "PASS" if passed else "BLOCKED",
            "runner": dict(RUNNER),
            "execution": {
                "run_id": f"run-{tc_id}",
                "job_id": f"job-{tc_id}",
                "tested_commit_sha": SHA,
                "environment": "ci-test",
                "started_at": START,
                "finished_at": END,
                "duration_ms": 10000,
            },
            "assertions": [
                {"assertion_id": "assert.ok", "status": "PASS", "evidence_ref": artifact_rel}
            ],
            "artifacts": [
                {
                    "artifact_id": "trace",
                    "kind": "trace",
                    "path": artifact_rel,
                    "sha256": _sha256(root, artifact_rel),
                }
            ],
            "blocked_reason": "" if passed else "fixture blocked",
        }
        if not traceable and passed:
            record["execution"] = {}
            record["assertions"] = []
            record["artifacts"] = []
        tests.append(record)
    results = {
        "schema_version": "2.0",
        "artifact_kind": "product-tc-results",
        "baseline_version": "v1.6.2",
        "commit_sha": SHA,
        "environment": "ci-test",
        "generated_at": END,
        "verification": {
            "verified": True,
            "verified_commit_sha": SHA,
            "verified_at": END,
            "verifier": {"name": "verify_product_tc_results", "version": "1.0.0"},
            "errors": [],
        },
        "tests": tests,
        "summary": {
            "product_tc_pass": results_pass,
            "product_tc_total": 10,
            "PASS": results_pass,
            "FAIL": 0,
            "BLOCKED": 10 - results_pass,
            "NOT_RUN": 0,
        },
    }
    _write_yaml(root, "docs/aiqe/v1.6/e2e/product-tc-config.yaml", config)
    _write_json(root, "docs/aiqe/v1.6/e2e/product-results.json", results)
    statuses = matrix_status or {f"TC-AIQE-{i:03d}": "PASS" for i in range(1, 11)}
    requirements = []
    for index in range(1, 11):
        tc_id = f"TC-AIQE-{index:03d}"
        product_status = statuses.get(tc_id, "PASS")
        requirements.append(
            {
                "id": tc_id,
                "status": product_status,
                "e2e": {"product": {"status": product_status}},
            }
        )
    _write_yaml(
        root,
        "docs/aiqe/v1.6/traceability/requirements.yaml",
        {
            "schema_version": "2.0",
            "baseline": {"release_commit": SHA, "migration_head": "20261122_v16_catalog_post_merge"},
            "requirements": requirements,
        },
    )
    _write(
        root,
        "docs/aiqe/v1.6/E2E-Coverage-and-Blockers.md",
        f"**产品级 TC PASS：{results_pass}/10。**\n",
    )
    return {"config": config, "results": results}


def _product_item(**overrides) -> dict:
    item = _closed_item(
        requirement_id="V16-017-R2",
        closure_rule_id="PRODUCT_TC_EXECUTED",
        inputs={
            "config": "docs/aiqe/v1.6/e2e/product-tc-config.yaml",
            "results": "docs/aiqe/v1.6/e2e/product-results.json",
            "matrix": "docs/aiqe/v1.6/traceability/requirements.yaml",
            "coverage": "docs/aiqe/v1.6/E2E-Coverage-and-Blockers.md",
        },
        evidence=[
            "docs/aiqe/v1.6/e2e/product-tc-config.yaml",
            "docs/aiqe/v1.6/e2e/product-results.json",
            "docs/aiqe/v1.6/traceability/requirements.yaml",
        ],
    )
    item.update(overrides)
    return item


def _runtime_index_fixture(root: Path, *, complete: bool) -> dict:
    tests = []
    for index in range(1, 11):
        tc_id = f"TC-PLATFORM-{index:03d}"
        if complete:
            record = {
                "tc_id": tc_id,
                "status": "PASS",
                "run_id": f"prun-{index}",
                "project_id": 1,
                "workflow_snapshot_hash": SNAPSHOT,
                "job_ids": [index],
                "node_run_ids": [f"node-{index}"],
                "assertion_ids": [f"assert-{index}"],
                "artifact_refs": [f"artifact-{index}"],
                "driver_image_digest": DIGEST,
                "duration_ms": 10000,
                "started_at": START,
                "finished_at": END,
            }
        else:
            record = {"tc_id": tc_id, "status": "PASS"}
        tests.append(record)
    payload = {
        "schema_version": "1.1",
        "generated_at": END,
        "commit_sha": SHA,
        "ci_run_id": "123456",
        "environment": "ci-test",
        "source": {"tested_commit_sha": SHA, "pr_head_sha": None, "merge_commit_sha": None,
                   "release_target_sha": None},
        "runtime": {"environment": "ci-test", "runtime_type": "container",
                    "driver_image_digest": DIGEST, "started_at": START, "finished_at": END,
                    "duration_ms": 10000},
        "workflow": {"run_id": "123456", "attempt": 1, "job_id": "job-1"},
        "artifacts": [
            {"name": "platform-results.json", "path": "docs/aiqe/v1.6/e2e/platform-results.json",
             "sha256": "1" * 64, "job_id": "job-1"}
        ],
        "tests": tests,
        "summary": {
            "PASS": 10,
            "FAIL": 0,
            "BLOCKED": 0,
            "NOT_RUN": 0,
            "total": 10,
            "executed": 10,
            "provenance_valid": True,
            "ga_ready": True,
        },
        "verification": {"provenance_valid": True, "errors": []},
    }
    rel = _write_json(root, "docs/aiqe/v1.6/evidence/evidence-index.json", payload)
    return {"rel": rel, "payload": payload}


def _runtime_index_item(**overrides) -> dict:
    item = _closed_item(
        requirement_id="V16-023-R1",
        closure_rule_id="RUNTIME_INDEX_CURRENT",
        inputs={"index": "docs/aiqe/v1.6/evidence/evidence-index.json", "require_tcs": 10},
        evidence=["docs/aiqe/v1.6/evidence/evidence-index.json"],
    )
    item.update(overrides)
    return item


# ---------------------------------------------------------------------------
# 手册 §13.5 场景 1：路径存在但内容不相关
# ---------------------------------------------------------------------------
def test_scenario_1_path_exists_but_content_irrelevant(tmp_path: Path):
    _write_json(tmp_path, "docs/aiqe/v1.6/evidence/credential-scan.json", {"unrelated": "value"})
    item = _closed_item(
        requirement_id="V16-021-R1",
        closure_rule_id="DOC_SEMANTICS",
        evidence=["docs/aiqe/v1.6/evidence/credential-scan.json"],
        inputs={
            "assertions": [
                {
                    "path": "docs/aiqe/v1.6/evidence/credential-scan.json",
                    "kind": "json",
                    "pointer": "status",
                    "equals": "CLEAN",
                }
            ]
        },
        artifact_hashes={
            "docs/aiqe/v1.6/evidence/credential-scan.json": _sha256(
                tmp_path, "docs/aiqe/v1.6/evidence/credential-scan.json"
            )
        },
    )
    errors, outcomes = _verify_closed(tmp_path, item)
    assert errors, "路径存在但内容不相关时不得 CLOSED"
    assert outcomes[0][1].status != "PASS"
    assert any("不存在" in reason or "缺少" in reason for reason in outcomes[0][1].reasons)


# ---------------------------------------------------------------------------
# 手册 §13.5 场景 2：TC Config runner null 不能关
# ---------------------------------------------------------------------------
def test_scenario_2_null_runner_cannot_close(tmp_path: Path):
    _product_fixture(tmp_path, runners="null", results_pass=10)
    errors, outcomes = _verify_closed(tmp_path, _product_item())
    assert errors, "runner 为 null 时 V16-017 不得 CLOSED"
    reasons = "；".join(outcomes[0][1].reasons)
    assert "runner" in reasons
    assert "runner 为 null" in reasons


def test_scenario_2b_null_runner_with_blocked_results_still_not_closable(tmp_path: Path):
    _product_fixture(tmp_path, runners="null", results_pass=0)
    errors, outcomes = _verify_closed(tmp_path, _product_item())
    assert errors
    assert outcomes[0][1].status != "PASS"


# ---------------------------------------------------------------------------
# 手册 §13.5 场景 3：10/10 但 runtime evidence 缺 8 项
# ---------------------------------------------------------------------------
def test_scenario_3_ten_of_ten_with_incomplete_runtime_evidence(tmp_path: Path):
    _runtime_index_fixture(tmp_path, complete=False)
    item = _runtime_index_item(
        artifact_hashes={
            "docs/aiqe/v1.6/evidence/evidence-index.json": _sha256(
                tmp_path, "docs/aiqe/v1.6/evidence/evidence-index.json"
            )
        }
    )
    errors, outcomes = _verify_closed(tmp_path, item)
    assert errors, "runtime evidence 缺少追溯字段时不得 CLOSED"
    reasons = "；".join(outcomes[0][1].reasons)
    for missing in ("job_ids", "node_run_ids", "assertion_ids", "artifact_refs"):
        assert missing in reasons
    assert outcomes[0][1].status != "PASS"


def test_scenario_3b_complete_runtime_index_passes_rule(tmp_path: Path):
    _runtime_index_fixture(tmp_path, complete=True)
    item = _runtime_index_item()
    errors, outcomes = _verify_closed(tmp_path, item)
    assert outcomes[0][1].status == "PASS", outcomes[0][1].as_dict()


# ---------------------------------------------------------------------------
# 手册 §13.5 场景 4：evidence commit 不是当前 SHA
# ---------------------------------------------------------------------------
def test_scenario_4_stale_scan_commit_cannot_close(tmp_path: Path):
    _write_json(
        tmp_path,
        "docs/aiqe/v1.6/evidence/credential-scan.json",
        {
            "scan_commit_sha": OLD_SHA,
            "generated_at": START,
            "status": "CLEAN",
            "summary": {"potential_secret": 0, "weak_default": 0},
        },
    )
    item = _closed_item(
        requirement_id="V16-021-R1",
        closure_rule_id="SECRET_SCAN_CURRENT",
        evidence=["docs/aiqe/v1.6/evidence/credential-scan.json"],
        inputs={"scan": "docs/aiqe/v1.6/evidence/credential-scan.json"},
        artifact_hashes={
            "docs/aiqe/v1.6/evidence/credential-scan.json": _sha256(
                tmp_path, "docs/aiqe/v1.6/evidence/credential-scan.json"
            )
        },
    )
    errors, outcomes = _verify_closed(tmp_path, item)
    assert errors, "扫描 SHA 不是当前验收 SHA 时不得 CLOSED"
    assert any("不是当前验收 SHA" in reason for reason in outcomes[0][1].reasons)


def test_scenario_4b_missing_scan_commit_cannot_close(tmp_path: Path):
    _write_json(
        tmp_path,
        "docs/aiqe/v1.6/evidence/credential-scan.json",
        {"generated_at": START, "status": "CLEAN", "summary": {"potential_secret": 0, "weak_default": 0}},
    )
    item = _closed_item(
        requirement_id="V16-021-R1",
        closure_rule_id="SECRET_SCAN_CURRENT",
        evidence=["docs/aiqe/v1.6/evidence/credential-scan.json"],
        inputs={"scan": "docs/aiqe/v1.6/evidence/credential-scan.json"},
        artifact_hashes={
            "docs/aiqe/v1.6/evidence/credential-scan.json": _sha256(
                tmp_path, "docs/aiqe/v1.6/evidence/credential-scan.json"
            )
        },
    )
    errors, outcomes = _verify_closed(tmp_path, item)
    assert errors
    assert any("scan_commit_sha" in reason for reason in outcomes[0][1].reasons)


# ---------------------------------------------------------------------------
# 手册 §13.5 场景 5：matrix 与 product result 矛盾
# ---------------------------------------------------------------------------
def test_scenario_5_matrix_result_conflict_reported(tmp_path: Path):
    statuses = {f"TC-AIQE-{i:03d}": "PASS" for i in range(1, 11)}
    _product_fixture(tmp_path, results_pass=1, matrix_status=statuses)
    errors, outcomes = _verify_closed(tmp_path, _product_item())
    assert errors, "matrix 与 product-results 矛盾时必须报冲突并拒绝 CLOSED"
    conflicts = "；".join(outcomes[0][1].conflicts)
    assert "矛盾" in conflicts or "不一致" in conflicts
    assert outcomes[0][1].status == "FAIL"


def test_scenario_5b_matrix_partial_vs_results_pass(tmp_path: Path):
    statuses = {f"TC-AIQE-{i:03d}": "PARTIAL" for i in range(1, 11)}
    _product_fixture(tmp_path, results_pass=10, matrix_status=statuses, traceable=False)
    errors, outcomes = _verify_closed(tmp_path, _product_item())
    assert errors
    assert any("matrix 产品状态" in reason for reason in outcomes[0][1].conflicts)


# ---------------------------------------------------------------------------
# 手册 §13.5 场景 6：证据完整且验证器通过 → 允许 CLOSED
# ---------------------------------------------------------------------------
def _base_ledger(root: Path) -> list[dict]:
    _write(root, "docs/fixture-note.md", "fixture evidence\n")
    items = []
    for item_id in CLOSURE.REQUIRED_IDS:
        items.append(
            {
                "id": item_id,
                "issue_id": item_id,
                "requirement_id": None,
                "title": f"fixture {item_id}",
                "status": "EXTERNAL",
                "closure_rule_id": "GENERIC_FILE_EVIDENCE",
                "rule_verdict": "NOT_PROVEN",
                "rule_checked_at": START,
                "evidence": ["docs/fixture-note.md"],
                "verified_commit_sha": None,
                "verifier": None,
                "artifact_hashes": {},
                "verified_at": None,
                "review": None,
                "downgrade_reason": "fixture downgrade",
                "blocked_by": "fixture",
                "owner": "fixture",
                "unblock_action": "fixture",
                "note": "fixture",
            }
        )
    return items


def _complete_ledger(root: Path) -> dict:
    _write(root, "docs/fixture_test.py", "def test_fixture_passes():\n    assert True\n")
    items = _base_ledger(root)
    items[0] = {
        "id": "P0-1",
        "issue_id": "P0-1",
        "requirement_id": "V16-025-R1",
        "title": "fixture closed item",
        "status": "CLOSED",
        "closure_rule_id": "TEST_EVIDENCE",
        "rule_verdict": "PASS",
        "rule_checked_at": START,
        "evidence": ["docs/fixture_test.py", "docs/fixture-note.md"],
        "inputs": {"test_ids": ["docs/fixture_test.py::test_fixture_passes"]},
        "verified_commit_sha": SHA,
        "verifier": {
            "name": "test_evidence_closure_verifier",
            "version": "1.0.0",
            "ci_run_id": "12345",
        },
        "artifact_hashes": {
            "docs/fixture_test.py": _sha256(root, "docs/fixture_test.py"),
            "docs/fixture-note.md": _sha256(root, "docs/fixture-note.md"),
        },
        "verified_at": START,
        "review": {
            "reviewer_login": "reviewer-x",
            "review_id": "PRR_123",
            "reviewed_commit_sha": SHA,
        },
        "note": "fixture close",
    }
    return {"items": items}


def test_scenario_6_complete_evidence_allows_closed(tmp_path: Path):
    ledger = _complete_ledger(tmp_path)
    assert CLOSURE.validate(ledger, root=tmp_path) == []
    errors, outcomes = CLOSURE.verify_closed(ledger, root=tmp_path, expected_commit=SHA)
    assert errors == []
    assert outcomes[0][1].status == "PASS"
    report = CLOSURE.render(ledger)
    assert "**CLOSED**" in report
    assert "PASS" in report


def test_scenario_6b_cli_check_passes_for_complete_ledger(tmp_path: Path):
    ledger = _complete_ledger(tmp_path)
    ledger_path = tmp_path / "docs/aiqe/v1.6/governance/audit-closure.yaml"
    _write_yaml(tmp_path, "docs/aiqe/v1.6/governance/audit-closure.yaml", ledger)
    report_path = tmp_path / "docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(CLOSURE.render(ledger) + "\n", encoding="utf-8", newline="\n")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--check",
            "--root",
            str(tmp_path),
            "--ledger",
            str(ledger_path),
            "--report",
            str(report_path),
            "--expected-commit",
            SHA,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_closure_registry_rules_are_executable():
    assert set(closure_rules.rule_ids()) >= {
        "PRODUCT_TC_EXECUTED",
        "RUNTIME_INDEX_CURRENT",
        "PROVENANCE_CONSISTENT",
        "SECRET_SCAN_CURRENT",
        "BRANCH_RULESET_REQUIRED_CHECKS",
        "TEST_EVIDENCE",
        "DOC_SEMANTICS",
        "GENERIC_FILE_EVIDENCE",
    }
    for rule_id in closure_rules.rule_ids():
        rule = closure_rules.get_rule(rule_id)
        assert rule is not None
        assert rule.verifier_name and rule.verifier_version
        assert callable(rule.func)
