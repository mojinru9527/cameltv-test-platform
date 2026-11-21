"""V16-025 验收：追踪矩阵门禁（check_traceability.py）自身必须拒绝不合格证据。"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

CHECKER_PATH = Path(__file__).resolve().parents[3] / "scripts" / "aiqe" / "check_traceability.py"


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
        "evidence": ["commit:09140401f"],
        "owner": "backend-security",
        "reviewer": "pending",
        "gaps": [],
    }
    entry.update(overrides)
    return entry


def _write_matrix(path: Path, entries: list[dict]) -> Path:
    text = "schema_version: '1.0'\nrelease: aiqe-v1.6\nbaseline:\n  main_sha: abc\nrequirements:\n"
    import yaml

    text += yaml.safe_dump({"requirements": entries}, allow_unicode=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture()
def checker(monkeypatch):
    module = _load_checker()
    # 单元测试只验证规则本身，覆盖集合收缩到当前被测 issue。
    monkeypatch.setattr(module, "REQUIRED_ISSUES", ("V16-001",))
    return module


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


def test_rejects_self_accepted_requirement(checker, tmp_path):
    entry = _base_entry(status="ACCEPTED", reviewer="backend-security")
    matrix = _write_matrix(tmp_path / "matrix.yaml", [entry])
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


def test_pr_mode_requires_issue_in_body(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    body = tmp_path / "pr.md"
    body.write_text("# PR\nRequirement ID: ...\n正式入口: ...\nMock: none\nReviewer: qa\n", encoding="utf-8")
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 1

    body.write_text(
        "# PR\nIssue: V16-001\nRequirement ID: V16-001-R1\n正式入口: job_consumer\nMock: none\nReviewer: qa\n",
        encoding="utf-8",
    )
    assert checker.main(["--matrix", str(matrix), "--issue", "V16-001", "--pr-body", str(body)]) == 0


def test_emit_evidence_index(checker, tmp_path):
    matrix = _write_matrix(tmp_path / "matrix.yaml", [_base_entry()])
    index_path = tmp_path / "evidence-index.json"
    assert checker.main(["--matrix", str(matrix), "--emit-evidence-index", str(index_path)]) == 0
    payload = json.loads(index_path.read_text(encoding="utf-8"))
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
