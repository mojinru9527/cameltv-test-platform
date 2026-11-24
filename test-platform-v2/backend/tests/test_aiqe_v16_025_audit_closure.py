"""V1.6 外部审计整改台账校验（check_audit_closure.py）。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/check_audit_closure.py"
LEDGER = REPO_ROOT / "docs/aiqe/v1.6/governance/audit-closure.yaml"
REPORT = REPO_ROOT / "docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md"


def _load():
    spec = importlib.util.spec_from_file_location("audit_closure", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


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
