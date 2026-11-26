"""V16-025：独立验收记录（acceptance/records）与角色独立性校验。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ACCEPTANCE = REPO_ROOT / "scripts/aiqe/acceptance_records.py"
CLI = REPO_ROOT / "scripts/aiqe/record_acceptance.py"
EXISTING_ARTIFACT = "docs/aiqe/v1.6/TC-010-User-Waiver.md"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


MODULE = _load(ACCEPTANCE, "acceptance_records")


def _record(**overrides) -> dict:
    record = {
        "requirement_id": "V16-001-R1",
        "decision": "REVIEWED",
        "reviewer": "qa-lead",
        "reviewed_at": "2026-11-24",
        "artifact": EXISTING_ARTIFACT,
    }
    record.update(overrides)
    return record


def _roles():
    return MODULE.load_role_matrix()


def test_valid_record_passes():
    errors = MODULE.validate_record(
        _record(), requirement_id="V16-001-R1", owner="backend-security", roles=_roles()
    )
    assert errors == []


def test_pending_reviewer_rejected():
    errors = MODULE.validate_record(
        _record(reviewer="pending"),
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
    )
    assert any("reviewer" in item for item in errors)


def test_same_role_domain_rejected():
    # owner qa-automation 与 reviewer qa-lead 同属 qa 角色域
    errors = MODULE.validate_record(
        _record(requirement_id="TC-AIQE-001", reviewer="qa-lead"),
        requirement_id="TC-AIQE-001",
        owner="qa-automation",
        roles=_roles(),
    )
    assert any("角色域" in item for item in errors), errors


def test_unknown_owner_rejected():
    errors = MODULE.validate_record(
        _record(requirement_id="V16-999-R1"),
        requirement_id="V16-999-R1",
        owner="someone-new",
        roles=_roles(),
    )
    assert any("未在 governance/review-roles.yaml 注册" in item for item in errors)


def test_missing_artifact_rejected():
    errors = MODULE.validate_record(
        _record(artifact="docs/aiqe/v1.6/acceptance/reviews/none.md"),
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
    )
    assert any("artifact 不存在" in item for item in errors)


def test_waived_requires_reason():
    errors = MODULE.validate_record(
        _record(decision="WAIVED", artifact=""),
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
    )
    assert any("waiver_reason" in item for item in errors)


def test_load_records_merges_valid_record(tmp_path):
    (tmp_path / "V16-001-R1.json").write_text(json.dumps(_record()), encoding="utf-8")
    entries = [
        {"id": "V16-001-R1", "owner": "backend-security", "status": "VERIFIED"},
        {"id": "V16-002-R1", "owner": "driver-device", "status": "VERIFIED"},
    ]
    report = MODULE.load_records(records_dir=tmp_path, entries=entries)
    assert report.errors == []
    merged = MODULE.apply_records(entries, report)
    acceptance = merged[0]["acceptance"]
    assert acceptance["status"] == "REVIEWED"
    assert acceptance["reviewer_role"] == "qa"
    assert acceptance["record"].endswith("V16-001-R1.json")
    assert merged[1].get("acceptance", {}).get("status", "NOT_REVIEWED") == "NOT_REVIEWED"


def test_record_for_unknown_requirement_rejected(tmp_path):
    (tmp_path / "V16-999-R1.json").write_text(
        json.dumps(_record(requirement_id="V16-999-R1")), encoding="utf-8"
    )
    report = MODULE.load_records(
        records_dir=tmp_path,
        entries=[{"id": "V16-001-R1", "owner": "backend-security"}],
    )
    assert any("未知 requirement_id" in item for item in report.errors)


def test_cli_writes_record(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--requirement",
            "V16-002-R1",
            "--reviewer",
            "qa-lead",
            "--reviewed-at",
            "2026-11-24",
            "--artifact",
            EXISTING_ARTIFACT,
            "--decision",
            "REVIEWED",
            "--records-dir",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    written = tmp_path / "V16-002-R1.json"
    assert written.exists()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["reviewer"] == "qa-lead" and payload["decision"] == "REVIEWED"


def test_cli_rejects_same_role_review(tmp_path):
    # owner qa-automation 与 reviewer qa-lead 同角色域
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--requirement",
            "TC-AIQE-002",
            "--reviewer",
            "qa-lead",
            "--reviewed-at",
            "2026-11-24",
            "--artifact",
            EXISTING_ARTIFACT,
            "--decision",
            "REVIEWED",
            "--records-dir",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 1
    assert "角色域" in result.stdout
