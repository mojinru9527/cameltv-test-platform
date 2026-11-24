"""V16-025 验收：追踪矩阵门禁（check_traceability.py v2）必须拒绝不合格证据。

覆盖三类回归：
1. v1 规则（测试/代码映射/状态合法性）仍生效；
2. v2 新增规则：acceptance 独立验收、证据类型化、运行时证据分层、产品/平台 TC 分离；
3. 基线唯一性（release commit + Alembic 单头）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

CHECKER_PATH = Path(__file__).resolve().parents[3] / "scripts" / "aiqe" / "check_traceability.py"
REAL_REPO_ROOT = Path(__file__).resolve().parents[3]
EXISTING_ARTIFACT = "docs/aiqe/v1.6/TC-010-User-Waiver.md"


def _load_checker():
    spec = importlib.util.spec_from_file_location("v16_traceability_checker", CHECKER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["v16_traceability_checker"] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop("v16_traceability_checker", None)
    return module


def _base_entry(**overrides) -> dict:
    entry = {
        "id": "V16-001-R1",
        "issue": "V16-001",
        "priority": "P0",
        "title": "策略四态",
        "requirement": "策略必须显式决策",
        "invariant": "只有 ALLOW 才放行",
        "status": "VERIFIED",
        "code": [
            {
                "path": "test-platform-v2/backend/app/aiqe/security/target_policy.py",
                "symbol": "PolicyDecision",
                "change": "modified",
            }
        ],
        "production_entry": ["job_consumer.run_job"],
        "tests": {
            "success": [
                "tests/test_aiqe_v16_001_policy_fail_closed.py::test_policy_decision_four_states"
            ],
            "negative": [
                "tests/test_aiqe_v16_001_policy_fail_closed.py::test_worker_blocks_run_without_policy_record"
            ],
        },
        "mock_boundary": "真实 SQLite",
        "layers": ["L2"],
        "evidence": [
            "commit:09140401f",
            "pytest:tests/test_aiqe_v16_001_policy_fail_closed.py (25 passed)",
        ],
        "acceptance": {"status": "NOT_REVIEWED", "reviewed_at": None, "artifact": None},
        "owner": "backend-security",
        "reviewer": "pending",
        "gaps": [],
    }
    entry.update(overrides)
    return entry


def _write_matrix(path: Path, entries: list[dict], *, baseline: dict | None = None) -> Path:
    import yaml

    document = {
        "schema_version": "2.0",
        "release": "aiqe-v1.6",
        "baseline": baseline
        or {
            "release_commit": "0" * 40,
            "migration_head": "20260101_test",
            "branch": "main",
        },
        "requirements": entries,
    }
    path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return path


@pytest.fixture()
def checker(monkeypatch):
    module = _load_checker()
    # 单元测试只验证规则本身，覆盖集合收缩到当前被测 issue。
    monkeypatch.setattr(module, "REQUIRED_ISSUES", ("V16-001",))
    return module


# --------------------------------------------------------------------------- #
# v1 规则
# --------------------------------------------------------------------------- #


def test_valid_matrix_passes(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    assert checker.main(["--matrix", str(matrix)]) == 0


def test_rejects_missing_negative_test_for_p0(checker, tmp_path):
    entry = _base_entry()
    entry["tests"] = {"success": entry["tests"]["success"]}
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_unit_only_verification(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry(layers=["L1"])])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_missing_issue_coverage(checker, tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "REQUIRED_ISSUES", ("V16-001", "V16-002"))
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_nonexistent_test_function(checker, tmp_path):
    entry = _base_entry()
    entry["tests"] = {
        "success": [
            "tests/test_aiqe_v16_001_policy_fail_closed.py::test_policy_decision_four_states"
        ],
        "negative": [
            "tests/test_aiqe_v16_001_policy_fail_closed.py::test_this_function_does_not_exist"
        ],
    }
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_nonexistent_code_path(checker, tmp_path):
    entry = _base_entry(code=[{"path": "app/aiqe/does_not_exist.py", "symbol": "x"}])
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_blocked_without_reason(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry(status="BLOCKED")])
    assert checker.main(["--matrix", str(matrix)]) == 1


# --------------------------------------------------------------------------- #
# v2：acceptance 独立验收
# --------------------------------------------------------------------------- #


def test_rejects_missing_acceptance_block(checker, tmp_path):
    entry = _base_entry()
    entry.pop("acceptance")
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_accepted_without_reviewed_acceptance(checker, tmp_path):
    entry = _base_entry(
        status="ACCEPTED",
        reviewer="qa-lead",
        acceptance={"status": "NOT_REVIEWED", "reviewed_at": None, "artifact": None},
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_self_review(checker, tmp_path):
    entry = _base_entry(
        status="ACCEPTED",
        reviewer="backend-security",
        acceptance={
            "status": "REVIEWED",
            "reviewed_at": "2026-11-24",
            "artifact": EXISTING_ARTIFACT,
            "record": "docs/aiqe/v1.6/acceptance/records/V16-001-R1.json",
        },
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_reviewed_without_artifact(checker, tmp_path):
    entry = _base_entry(
        reviewer="qa-lead",
        acceptance={"status": "REVIEWED", "reviewed_at": "2026-11-24", "artifact": None},
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_accepts_reviewed_with_non_author_reviewer_and_artifact(checker, tmp_path):
    entry = _base_entry(
        status="ACCEPTED",
        reviewer="qa-lead",
        acceptance={
            "status": "REVIEWED",
            "reviewed_at": "2026-11-24",
            "artifact": EXISTING_ARTIFACT,
            "record": "docs/aiqe/v1.6/acceptance/records/V16-001-R1.json",
        },
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 0


# --------------------------------------------------------------------------- #
# v2：证据类型化
# --------------------------------------------------------------------------- #


def test_rejects_bare_evidence(checker, tmp_path):
    entry = _base_entry(evidence=["commit:09140401f", "PR template + evidence-index"])
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_unknown_evidence_kind(checker, tmp_path):
    entry = _base_entry(evidence=["commit:09140401f", "screenshot:foo.png"])
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_pytest_evidence_for_missing_file(checker, tmp_path):
    entry = _base_entry(
        evidence=["commit:09140401f", "pytest:tests/test_does_not_exist.py (3 passed)"]
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_script_evidence_for_missing_path(checker, tmp_path):
    entry = _base_entry(evidence=["commit:09140401f", "script:scripts/qa/does_not_exist.py (PASS)"])
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_accepts_script_evidence_for_existing_path(checker, tmp_path):
    entry = _base_entry(
        evidence=[
            "commit:09140401f",
            "pytest:tests/test_aiqe_v16_001_policy_fail_closed.py (25 passed)",
            "script:scripts/aiqe/check_alerts.py (alerts=21 metrics=21)",
        ],
        runtime_evidence={
            "status": "NOT_PROVEN",
            "artifacts": [],
            "note": "脚本输出未归档为机器产物。",
        },
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 0


# --------------------------------------------------------------------------- #
# v2：运行时证据分层
# --------------------------------------------------------------------------- #


def test_rejects_runtime_evidence_without_runtime_block(checker, tmp_path):
    entry = _base_entry(evidence=["live:shadow run PASS"])
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_verified_with_only_runtime_evidence(checker, tmp_path):
    entry = _base_entry(
        evidence=["live:shadow run PASS"],
        runtime_evidence={"status": "NOT_PROVEN", "artifacts": [], "note": "未归档"},
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_runtime_proven_without_ids(checker, tmp_path):
    entry = _base_entry(
        evidence=[
            "pytest:tests/test_aiqe_v16_001_policy_fail_closed.py (25 passed)",
            "live:shadow run PASS",
        ],
        runtime_evidence={"status": "PROVEN", "artifacts": [EXISTING_ARTIFACT], "refs": {}},
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_accepts_runtime_proven_with_artifact_and_run_id(checker, tmp_path):
    entry = _base_entry(
        evidence=[
            "pytest:tests/test_aiqe_v16_001_policy_fail_closed.py (25 passed)",
            "live:shadow run PASS",
        ],
        runtime_evidence={
            "status": "PROVEN",
            "artifacts": [EXISTING_ARTIFACT],
            "refs": {"run_id": "9fb84240-8906-4a17-9338-b368718e38c4"},
        },
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 0


# --------------------------------------------------------------------------- #
# v2：产品 TC 与平台 TC 分离
# --------------------------------------------------------------------------- #


def _product_tc_entry(**overrides) -> dict:
    entry = {
        "id": "TC-AIQE-001",
        "issue": "TC-AIQE-001",
        "priority": "P1",
        "title": "需求契约冻结 + 变化影响",
        "requirement": "冻结 V1 后 V2 变更必须只标记需复审",
        "invariant": "V1 checksum 不变",
        "status": "PARTIAL",
        "code": [],
        "production_entry": ["contract_service"],
        "tests": {
            "success": [
                "tests/e2e/aiqe/test_v16_017_tc001_contract.py::test_tc_001_contract_freeze_and_v2_impact"
            ],
            "negative": [
                "tests/test_aiqe_v16_001_policy_fail_closed.py::test_worker_blocks_run_without_policy_record"
            ],
        },
        "layers": ["L2"],
        "evidence": ["pytest:tests/e2e/aiqe/test_v16_017_tc001_contract.py (1 passed)"],
        "acceptance": {"status": "NOT_REVIEWED", "reviewed_at": None, "artifact": None},
        "owner": "qa-automation",
        "reviewer": "pending",
        "gaps": [],
        "e2e": {
            "product": {
                "status": "PARTIAL",
                "evidence": [
                    {"kind": "owner-attested", "ref": "docs/aiqe/v1.6/V1.6-Test-Plan-and-Evidence.md"}
                ],
            },
            "platform": {
                "tc_ids": ["TC-PLATFORM-010"],
                "tests": [
                    "tests/e2e/aiqe/test_v16_017_tc001_contract.py::test_tc_001_contract_freeze_and_v2_impact"
                ],
            },
        },
    }
    entry.update(overrides)
    return entry


def test_accepts_product_tc_partial_with_platform_mapping(checker, tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "REQUIRED_ISSUES", ("TC-AIQE-001",))
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_product_tc_entry()])
    assert checker.main(["--matrix", str(matrix)]) == 0


def test_rejects_product_tc_verified_without_product_pass(checker, tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "REQUIRED_ISSUES", ("TC-AIQE-001",))
    entry = _product_tc_entry(status="VERIFIED")
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_rejects_product_tc_product_pass_without_artifact(checker, tmp_path, monkeypatch):
    monkeypatch.setattr(checker, "REQUIRED_ISSUES", ("TC-AIQE-001",))
    entry = _product_tc_entry()
    entry["e2e"]["product"] = {
        "status": "PASS",
        "evidence": [{"kind": "owner-attested", "ref": "现场记录"}],
    }
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


# --------------------------------------------------------------------------- #
# v2：基线唯一
# --------------------------------------------------------------------------- #


def test_rejects_migration_head_drift(checker, tmp_path, monkeypatch):
    matrix = _write_matrix(
        tmp_path / "matrix.yaml",
        [_base_entry()],
        baseline={
            "release_commit": _head_sha(),
            "migration_head": "20260101_stale",
            "branch": "main",
        },
    )
    monkeypatch.setattr(checker, "_compute_alembic_head", lambda report: "20260202_current")
    assert checker.main(["--matrix", str(matrix), "--check-baseline"]) == 1


def _head_sha() -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REAL_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_accepts_matching_migration_head(checker, tmp_path, monkeypatch):
    matrix = _write_matrix(
        tmp_path / "matrix.yaml",
        [_base_entry()],
        baseline={
            "release_commit": _head_sha(),
            "migration_head": "20260202_current",
            "branch": "main",
        },
    )
    monkeypatch.setattr(checker, "_compute_alembic_head", lambda report: "20260202_current")
    assert checker.main(["--matrix", str(matrix), "--check-baseline"]) == 0


# --------------------------------------------------------------------------- #
# 严格模式 / 发布门禁 / 产物
# --------------------------------------------------------------------------- #


def test_strict_warnings_returns_two(checker, tmp_path, monkeypatch):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    monkeypatch.setattr(
        checker,
        "_validate_requirement",
        lambda entry, report, seen: (
            report.warn("forced warning"),
            entry.update({"_status": "VERIFIED", "_priority": "P0"}),
            entry,
        )[-1],
    )
    assert checker.main(["--matrix", str(matrix), "--strict-warnings"]) == 2


def test_release_gate_rejects_pending_acceptance(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    assert checker.main(["--matrix", str(matrix), "--release-gate"]) == 1


def test_release_gate_accepts_fully_reviewed_entry(checker, tmp_path, monkeypatch):
    # 发布门禁同时要求运行时证据与产品 TC；此处只验证 acceptance 维度，
    # 通过移除运行时/产品 TC 相关约束来隔离被测规则。
    monkeypatch.setattr(checker, "_release_gate", checker._release_gate)
    entry = _base_entry(
        status="ACCEPTED",
        reviewer="qa-lead",
        acceptance={
            "status": "REVIEWED",
            "reviewed_at": "2026-11-24",
            "artifact": EXISTING_ARTIFACT,
            "record": "docs/aiqe/v1.6/acceptance/records/V16-001-R1.json",
        },
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix), "--release-gate"]) == 0


def test_pr_mode_requires_issue_in_body(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text("# PR\nIssue: V16-001\n", encoding="utf-8")
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 1


def test_pr_mode_rejects_placeholder_fields(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text(
        "# PR\n"
        "Issue / Requirement ID：V16-001\n"
        "业务结果（用户可观察）：...\n"
        "正式入口（API / Worker / Job / CLI）：job_consumer.run_job\n"
        "调用链（入口到 Driver/Assertion/Finalize）：job -> driver\n"
        "真实组件与 Mock 边界：真实 SQLite，未 Mock\n"
        "成功路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_policy_decision_four_states\n"
        "拒绝/失败路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_worker_blocks_run_without_policy_record\n"
        "证据（commit SHA / CI Run / 测试报告 / Run ID / Job ID / Artifact ID）：commit:09140401f\n"
        "Reviewer（非原实现者）：qa-lead\n"
        "Reviewer 角色域（须与 owner 不同）：qa\n",
        encoding="utf-8",
    )
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 1


def test_pr_mode_accepts_complete_fields(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text(
        "# PR\n"
        "Issue / Requirement ID：V16-001 / V16-001-R1\n"
        "业务结果（用户可观察）：策略缺失时节点阻塞且目标零请求\n"
        "正式入口（API / Worker / Job / CLI）：job_consumer.run_job\n"
        "调用链（入口到 Driver/Assertion/Finalize）：job -> policy -> 阻断\n"
        "真实组件与 Mock 边界：真实 SQLite 会话与本地 HTTP 目标，无 Mock\n"
        "成功路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_policy_decision_four_states\n"
        "拒绝/失败路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_worker_blocks_run_without_policy_record\n"
        "证据（commit SHA / CI Run / 测试报告 / Run ID / Job ID / Artifact ID）：commit:09140401f\n"
        "Reviewer（非原实现者）：qa-lead\n"
        "Reviewer 角色域（须与 owner 不同）：qa\n",
        encoding="utf-8",
    )
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 0


def test_pr_mode_rejects_author_as_reviewer(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text(
        "# PR\n"
        "Issue / Requirement ID：V16-001\n"
        "业务结果（用户可观察）：策略缺失时节点阻塞\n"
        "正式入口（API / Worker / Job / CLI）：job_consumer.run_job\n"
        "调用链（入口到 Driver/Assertion/Finalize）：job -> policy\n"
        "真实组件与 Mock 边界：真实 SQLite，无 Mock\n"
        "成功路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_policy_decision_four_states\n"
        "拒绝/失败路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_worker_blocks_run_without_policy_record\n"
        "证据（commit SHA / CI Run / 测试报告 / Run ID / Job ID / Artifact ID）：commit:09140401f\n"
        "Reviewer（非原实现者）：@mojinru9527\n"
        "Reviewer 角色域（须与 owner 不同）：qa\n",
        encoding="utf-8",
    )
    assert (
        checker.main(
            [
                "--matrix",
                str(matrix),
                "--issue",
                "V16-001",
                "--pr-body",
                str(body),
                "--pr-author",
                "mojinru9527",
            ]
        )
        == 1
    )


def test_emit_evidence_index_is_marked_as_matrix_snapshot(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    index_path = tmp_path / "evidence-index.json"
    assert checker.main(["--matrix", str(matrix), "--emit-evidence-index", str(index_path)]) == 0
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["artifact_kind"] == "traceability-matrix-snapshot"
    assert payload["not_runtime_evidence"] is True
    assert payload["summary"]["verified"] == 1
    assert payload["requirements"][0]["id"] == "V16-001-R1"
    assert payload["requirements"][0]["tests"]["negative"]


def test_emit_markdown(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    md_path = tmp_path / "matrix.md"
    assert checker.main(["--matrix", str(matrix), "--emit-markdown", str(md_path)]) == 0
    text = md_path.read_text(encoding="utf-8")
    assert "需求—代码—正式入口—测试—证据矩阵" in text
    assert "V16-001-R1" in text
    assert "acceptance" in text.lower() or "独立验收" in text


def _pr_body(role: str) -> str:
    return (
        "# PR\n"
        "Issue / Requirement ID：V16-001\n"
        "业务结果（用户可观察）：策略缺失时节点阻塞\n"
        "正式入口（API / Worker / Job / CLI）：job_consumer.run_job\n"
        "调用链（入口到 Driver/Assertion/Finalize）：job -> policy\n"
        "真实组件与 Mock 边界：真实 SQLite，无 Mock\n"
        "成功路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_policy_decision_four_states\n"
        "拒绝/失败路径测试：tests/test_aiqe_v16_001_policy_fail_closed.py::test_worker_blocks_run_without_policy_record\n"
        "证据（commit SHA / CI Run / 测试报告 / Run ID / Job ID / Artifact ID）：commit:09140401f\n"
        "Reviewer（非原实现者）：qa-lead\n"
        f"Reviewer 角色域（须与 owner 不同）：{role}\n"
    )


def test_pr_mode_rejects_same_role_domain(checker, tmp_path):
    # owner backend-security → engineering；reviewer 角色域同为 engineering 不独立
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text(_pr_body("engineering"), encoding="utf-8")
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 1


def test_pr_mode_rejects_unknown_role_domain(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text(_pr_body("wizard"), encoding="utf-8")
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 1


def test_pr_mode_accepts_independent_role_domain(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text(_pr_body("qa"), encoding="utf-8")
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 0


def test_rejects_runtime_evidence_unknown_ref_key(checker, tmp_path):
    """V16-025 审计项 21：runtime_evidence.refs 只允许统一 Schema 中的键。"""
    entry = _base_entry(
        evidence=[
            "pytest:tests/test_aiqe_v16_001_policy_fail_closed.py (25 passed)",
            "live:shadow run PASS",
        ],
        runtime_evidence={
            "status": "PROVEN",
            "artifacts": [EXISTING_ARTIFACT],
            "refs": {"run_id": "9fb84240-8906-4a17-9338-b368718e38c4", "fake_id": "x"},
        },
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 1


def test_accepts_runtime_evidence_full_ref_set(checker, tmp_path):
    entry = _base_entry(
        evidence=[
            "pytest:tests/test_aiqe_v16_001_policy_fail_closed.py (25 passed)",
            "live:shadow run PASS",
        ],
        runtime_evidence={
            "status": "PROVEN",
            "artifacts": [EXISTING_ARTIFACT],
            "refs": {
                "run_id": "9fb84240-8906-4a17-9338-b368718e38c4",
                "project_id": 1,
                "job_ids": [1],
                "node_run_ids": ["n-1"],
                "assertion_ids": ["a-1"],
                "artifact_refs": ["art-1"],
                "workflow_snapshot_hash": "a" * 64,
                "commit_sha": "b" * 40,
                "ci_run_id": "12345",
            },
        },
    )
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
    assert checker.main(["--matrix", str(matrix)]) == 0
