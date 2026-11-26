"""V16-004：PostgreSQL 只读角色验证脚本 + 证据状态回归。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/check_pg_readonly_role.py"
EVIDENCE = REPO_ROOT / "docs/aiqe/v1.6/evidence/pg-readonly-role.json"


def _load():
    spec = importlib.util.spec_from_file_location("pg_readonly", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_mask_dsn_hides_password():
    masked = MODULE.mask_dsn("postgresql://aiqe_ro:secret@db.example:5432/cameltv")
    assert "secret" not in masked
    assert "aiqe_ro" in masked and "db.example" in masked and "5432" in masked


def test_mask_dsn_without_password_unchanged():
    dsn = "postgresql://aiqe_ro@db.example:5432/cameltv"
    assert MODULE.mask_dsn(dsn) == dsn


def test_no_dsn_returns_not_proven(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 2
    assert "NOT_PROVEN" in result.stdout


def test_unreachable_dsn_reports_fail(tmp_path):
    output = tmp_path / "pg.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--check",
            "--dsn",
            "postgresql://aiqe_ro:secret@127.0.0.1:1/cameltv",
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "FAIL"
    assert "secret" not in json.dumps(payload)


def test_committed_evidence_is_honest():
    """仓库内证据不得伪称 PASS：要么 NOT_PROVEN，要么有真实检查明细。"""
    assert EVIDENCE.exists()
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["artifact_kind"] == "pg-readonly-role-verification"
    if payload["status"] == "PASS":
        assert payload.get("checks") and all(item.get("ok") for item in payload["checks"])
        assert payload.get("dsn") and "secret" not in json.dumps(payload)
    else:
        assert payload["status"] in {"NOT_PROVEN", "FAIL"}
        assert payload.get("reason") or payload.get("error")

def test_scope_marks_loopback_vs_remote():
    assert MODULE._scope("postgresql://u:p@127.0.0.1:5432/db") == "loopback"
    assert MODULE._scope("postgresql://u:p@localhost:5432/db") == "loopback"
    assert MODULE._scope("postgresql://u:p@db.example:5432/db") == "remote"


def test_committed_pass_evidence_declares_scope_and_version():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if payload["status"] != "PASS":
        return
    assert payload.get("scope") in {"loopback", "remote"}
    assert payload.get("server_version")
