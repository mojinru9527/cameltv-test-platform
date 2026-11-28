"""V1.6 外部审计整改台账校验（check_audit_closure.py）。

FIX-012 扩展（2026-11-28）：关闭记录必须带 closure_rule_id / verified_commit_sha /
verifier / artifact_hashes / verified_at / 真实 review，并由语义规则验证。
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/check_audit_closure.py"
LEDGER = REPO_ROOT / "docs/aiqe/v1.6/governance/audit-closure.yaml"
REPORT = REPO_ROOT / "docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md"
SCRIPTS = REPO_ROOT / "scripts/aiqe"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from validators import closure_rules  # noqa: E402


def _load():
    spec = importlib.util.spec_from_file_location("audit_closure", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load()
EVIDENCE = "docs/aiqe/v1.6/governance/branch-protection.json"


def _closed_item(**overrides):
    item = {
        "id": "P0-1",
        "issue_id": "P0-1",
        "requirement_id": "V16-025-R1",
        "title": "fixture",
        "status": "CLOSED",
        "closure_rule_id": "GENERIC_FILE_EVIDENCE",
        "evidence": [EVIDENCE],
        "verified_commit_sha": "a" * 40,
        "verifier": {"name": "fixture", "version": "1.0", "ci_run_id": "123"},
        "artifact_hashes": {},
        "verified_at": "2026-11-28T00:00:00Z",
        "review": {
            "reviewer_login": "reviewer",
            "review_id": "PRR_1",
            "reviewed_commit_sha": "a" * 40,
        },
        "note": "fixture",
    }
    item.update(overrides)
    return item


def _external_item(**overrides):
    item = {
        "id": "P0-2",
        "issue_id": "P0-2",
        "requirement_id": "V16-025-R1",
        "title": "fixture",
        "status": "EXTERNAL",
        "closure_rule_id": "BRANCH_RULESET_REQUIRED_CHECKS",
        "evidence": [EVIDENCE],
        "downgrade_reason": "缺真实 review",
        "blocked_by": "x",
        "owner": "y",
        "unblock_action": "z",
    }
    item.update(overrides)
    return item


def test_ledger_covers_required_audit_items():
    ledger = MODULE.load_ledger()
    ids = {str(item.get("id")) for item in ledger.get("items") or []}
    assert set(MODULE.REQUIRED_IDS).issubset(ids)
    assert MODULE.validate(ledger) == []


def test_closed_item_requires_existing_evidence(tmp_path):
    ledger = {
        "items": [
            {
                "id": "P0-1",
                "title": "x",
                "status": "CLOSED",
                "evidence": ["docs/aiqe/v1.6/does-not-exist.md"],
                "note": "x",
            }
        ]
    }
    errors = MODULE.validate(ledger)
    assert any("evidence 路径不存在" in item for item in errors)


def test_external_item_requires_blocker_owner_action():
    ledger = {
        "items": [
            {
                "id": "P0-2",
                "title": "x",
                "status": "EXTERNAL",
                "evidence": ["docs/aiqe/v1.6/governance/branch-protection.json"],
            }
        ]
    }
    errors = MODULE.validate(ledger)
    for field in ("blocked_by", "owner", "unblock_action"):
        assert any(field in item for item in errors), (field, errors)


def test_missing_required_item_rejected():
    ledger = {"items": [{"id": "P0-1", "title": "x", "status": "CLOSED", "evidence": ["README.md"]}]}
    errors = MODULE.validate(ledger)
    assert any("台账缺少审计条目" in item for item in errors)


def test_report_is_fresh_and_check_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_generated_report_marks_closed_and_external():
    text = REPORT.read_text(encoding="utf-8")
    assert "V1.6 外部审计整改报告" in text
    assert "| CLOSED" in text and "| EXTERNAL" in text
    ledger = MODULE.load_ledger()
    closed = sum(1 for item in ledger["items"] if item["status"] == "CLOSED")
    external = sum(1 for item in ledger["items"] if item["status"] == "EXTERNAL")
    assert f"| **{closed + external}** |" in text


# ---------------------------------------------------------------------------
# FIX-012：关闭记录结构 + 语义验证
# ---------------------------------------------------------------------------
def test_registry_contains_required_rules():
    for rule_id in (
        "PRODUCT_TC_EXECUTED",
        "RUNTIME_INDEX_CURRENT",
        "PROVENANCE_CONSISTENT",
        "SECRET_SCAN_CURRENT",
        "BRANCH_RULESET_REQUIRED_CHECKS",
        "TEST_EVIDENCE",
        "DOC_SEMANTICS",
        "GENERIC_FILE_EVIDENCE",
    ):
        rule = closure_rules.get_rule(rule_id)
        assert rule is not None, rule_id
        assert rule.verifier_name and rule.verifier_version


def test_missing_closure_rule_rejected():
    ledger = {"items": [_external_item(closure_rule_id="")]}
    errors = MODULE.validate(ledger)
    assert any("缺少 closure_rule_id" in item for item in errors)


def test_unregistered_closure_rule_rejected():
    ledger = {"items": [_external_item(closure_rule_id="NOT_A_RULE")]}
    errors = MODULE.validate(ledger)
    assert any("closure_rule_id 未注册" in item for item in errors)


def test_external_requires_downgrade_reason():
    ledger = {"items": [_external_item(downgrade_reason="")]}
    errors = MODULE.validate(ledger)
    assert any("downgrade_reason" in item for item in errors)


def test_closed_requires_verified_sha_and_verifier():
    ledger = {"items": [_closed_item(verified_commit_sha="", verifier={})]}
    errors = MODULE.validate(ledger)
    assert any("verified_commit_sha" in item for item in errors)
    for field in ("name", "version", "ci_run_id"):
        assert any(field in item for item in errors), (field, errors)


def test_closed_without_real_review_must_downgrade():
    ledger = {"items": [_closed_item(review={})]}
    errors = MODULE.validate(ledger)
    assert any("真实 GitHub review" in item for item in errors)


def test_closed_review_sha_must_match_verified_sha():
    ledger = {
        "items": [
            _closed_item(
                review={
                    "reviewer_login": "reviewer",
                    "review_id": "PRR_1",
                    "reviewed_commit_sha": "b" * 40,
                }
            )
        ]
    }
    errors = MODULE.validate(ledger)
    assert any("review.reviewed_commit_sha" in item for item in errors)


def test_closed_artifact_hash_mismatch_rejected():
    ledger = {
        "items": [
            _closed_item(artifact_hashes={EVIDENCE: "0" * 64}),
        ]
    }
    errors = MODULE.validate(ledger)
    assert any("artifact_hashes 与" in item for item in errors)


def test_closed_requires_verified_at():
    ledger = {"items": [_closed_item(verified_at=None)]}
    errors = MODULE.validate(ledger)
    assert any("verified_at" in item for item in errors)


def test_verify_closed_reports_rule_failure(tmp_path):
    item = _closed_item(
        closure_rule_id="BRANCH_RULESET_REQUIRED_CHECKS",
        evidence=["docs/aiqe/v1.6/governance/branch-protection.json"],
    )
    # 使用空 root：规则必须因证据缺失/无效而失败，不依赖线上 Ruleset 当前状态。
    errors, outcomes = MODULE.verify_closed({"items": [item]}, root=tmp_path)
    assert errors and "未通过语义验证" in errors[0]
    assert outcomes[0][1].status != "PASS"


def test_external_rule_failure_is_not_an_error(tmp_path):
    item = _external_item(closure_rule_id="BRANCH_RULESET_REQUIRED_CHECKS")
    errors, outcomes = MODULE.verify_closed({"items": [item]}, root=tmp_path)
    assert errors == []
    assert outcomes[0][1].status in {"FAIL", "NOT_PROVEN"}


def test_verify_closed_rejects_stale_verified_commit():
    ledger = {"items": [_closed_item(closure_rule_id="GENERIC_FILE_EVIDENCE")]}
    errors, _ = MODULE.verify_closed(ledger, expected_commit="f" * 40)
    assert any("不是当前验收 SHA" in item for item in errors)


def test_report_lists_rule_verifier_sha_and_reasons():
    text = REPORT.read_text(encoding="utf-8")
    assert "关闭规则注册表" in text
    for rule_id in ("PRODUCT_TC_EXECUTED", "SECRET_SCAN_CURRENT", "BRANCH_RULESET_REQUIRED_CHECKS"):
        assert rule_id in text
    assert "验证器" in text and "已验证 SHA" in text
    assert "未通过原因" in text
    assert "product_tc_closure_verifier@1.0.0" in text


def test_check_returns_nonzero_when_closed_rule_fails(tmp_path):
    (tmp_path / "docs").mkdir()
    text = "# V1.6 外部审计整改报告（机器生成）\n"
    report = tmp_path / "docs/report.md"
    report.write_text(text, encoding="utf-8")
    ledger = {"items": [_closed_item(closure_rule_id="BRANCH_RULESET_REQUIRED_CHECKS")]}
    ledger_path = tmp_path / "docs/audit-closure.yaml"
    import yaml

    ledger_path.write_text(yaml.safe_dump(ledger, allow_unicode=True), encoding="utf-8")
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
            str(report),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode != 0
    assert "未通过语义验证" in result.stdout
