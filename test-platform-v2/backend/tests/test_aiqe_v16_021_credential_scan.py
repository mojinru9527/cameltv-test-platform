"""V16-021/P2-3：仓库历史弱凭据扫描脚本的离线单测。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/scan_credentials.py"


def _load():
    spec = importlib.util.spec_from_file_location("scan_credentials", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_mask_value_hides_secret():
    masked = MODULE.mask_value("postgresql://user:secret@db.example:5432/db")
    assert "secret" not in masked
    assert masked.startswith("po") and "len=" in masked


def test_classify_localhost_dsn_is_weak_default():
    import re

    match = MODULE.DSN.search("postgresql://cameltv:cameltv_test@localhost:5432/cameltv_test")
    assert match is not None
    assert MODULE.classify("dsn_with_password", match.group(0), "x.yml", "DATABASE_URL: ...") == "weak-default"


def test_classify_example_dsn_is_placeholder():
    match = MODULE.DSN.search("mysql://ro_user:***@db.example:3306/hz")
    assert match is not None
    assert MODULE.classify("dsn_with_password", match.group(0), "x.py", "FUTUREWAYU_DB_READONLY_DSN=...") == "placeholder"


def test_skip_path_excludes_docs_tests_and_examples():
    for path in ("docs/x.md", "tests/x.py", "a/__tests__/b.test.ts", "deploy/x.example.json"):
        assert MODULE.skip_path(path), path
    assert not MODULE.skip_path(".github/workflows/ci.yml")


def test_config_file_scope():
    assert MODULE.is_config_file(".env")
    assert MODULE.is_config_file(".github/workflows/ci.yml")
    assert MODULE.is_config_file("deploy/release-manifest.json")
    assert not MODULE.is_config_file("app/main.py")


def test_scan_text_flags_quoted_token_in_config():
    findings = MODULE.scan_text('token = "abc123def456"\n', path="deploy/config.yml")
    assert findings and findings[0]["classification"] in {"potential-secret", "weak-default"}
    assert "abc123" not in findings[0]["masked"]
