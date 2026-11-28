"""V16-021 / FIX-009：凭据扫描器与新脚本 Secret 语义的离线单测。

覆盖：Playwright .fill/.send_keys、Markdown 明文口令、Authorization/Bearer/Cookie、
URL basic auth、DSN、私钥、分级计数（不得把 weak-default 报 CLEAN）、scan_commit_sha、
新增/修改文件扫描范围、治理例外，以及缺失 Secret 时 Runner BLOCKED 且不回退默认值。
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AIQE_DIR = REPO_ROOT / "scripts/aiqe"
SCRIPT = AIQE_DIR / "scan_credentials.py"
REMEMBER = AIQE_DIR / "per_tc/futurewayu_remember_account.py"
MULTI_END = AIQE_DIR / "per_tc/futurewayu_multi_end.py"
OVERLAY = AIQE_DIR / "per_tc/futurewayu_overlay_interference.py"

if str(AIQE_DIR) not in sys.path:
    sys.path.insert(0, str(AIQE_DIR))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load("vw162_credential_scan", SCRIPT)
REMEMBER_MODULE = _load("vw162_credential_scan_remember", REMEMBER)
MULTI_END_MODULE = _load("vw162_credential_scan_multi_end", MULTI_END)
OVERLAY_MODULE = _load("vw162_credential_scan_overlay", OVERLAY)


# ── 兼容旧行为 ──────────────────────────────────────────────
def test_mask_value_hides_secret():
    masked = MODULE.mask_value("postgresql://user:secret@db.example:5432/db")
    assert "secret" not in masked
    assert masked.startswith("po") and "len=" in masked


def test_mask_value_short_values_only_keep_length():
    assert MODULE.mask_value("123456") == "*** (len=6)"


def test_classify_localhost_dsn_is_weak_default():
    match = MODULE.DSN.search("postgresql://cameltv:cameltv_test@localhost:5432/cameltv_test")
    assert match is not None
    assert (
        MODULE.classify("dsn_with_password", match.group(0), "x.yml", "DATABASE_URL: ...")
        == "weak-default"
    )


def test_classify_example_dsn_is_placeholder():
    match = MODULE.DSN.search("mysql://ro_user:***@db.example:3306/hz")
    assert match is not None
    assert (
        MODULE.classify("dsn_with_password", match.group(0), "x.py", "FUTUREWAYU_DB_READONLY_DSN=...")
        == "placeholder"
    )


def test_config_file_scope():
    assert MODULE.is_config_file(".env")
    assert MODULE.is_config_file(".github/workflows/ci.yml")
    assert MODULE.is_config_file("deploy/release-manifest.json")
    assert not MODULE.is_config_file("app/main.py")


def test_scan_text_flags_quoted_token_in_config():
    findings = MODULE.scan_text('token = "abc123def456"\n', path="deploy/config.yml")
    assert findings and findings[0]["classification"] in {"potential-secret", "weak-default"}
    assert "abc123" not in findings[0]["masked"]


# ── FIX-009：新增扫描范围与模式 ──────────────────────────────
def test_skip_path_only_excludes_generated_binary_and_vendor():
    assert MODULE.skip_path("node_modules/pkg/index.js")
    assert MODULE.skip_path("test-platform-v2/frontend/node_modules/x.ts")
    assert MODULE.skip_path("docs/aiqe/v1.6/evidence/credential-scan.json")
    assert MODULE.skip_path("test-platform-v2/frontend/dist/assets/index.js")
    # 文档与工作流必须在扫描范围内（旧扫描器整体排除 docs/ 导致明文漏检）
    assert not MODULE.skip_path("docs/aiqe/v1.6/e2e/TC-AIQE-008-Retest-20261127.md")
    assert not MODULE.skip_path(".github/workflows/main-quality-gate.yml")
    assert MODULE.exclusion_reason("node_modules/pkg/index.js")


def test_fill_hardcoded_password_is_detected():
    text = 'page.locator(\'input[placeholder="密码"]\').fill("hardcoded-password")\n'
    findings = MODULE.scan_text(text, path="scripts/aiqe/per_tc/demo.py")
    assert findings, "Playwright .fill(\"...\") 明文密码必须被识别"
    assert findings[0]["kind"] == "hardcoded_password"
    assert findings[0]["classification"] == "potential-secret"
    assert "hardcoded-password" not in findings[0]["masked"]
    assert "hardcoded-password" not in json.dumps(findings, ensure_ascii=False)


def test_fill_username_is_detected():
    text = 'page.locator(\'input[placeholder="用户名"]\').fill("tester-operator")\n'
    findings = MODULE.scan_text(text, path="scripts/aiqe/per_tc/demo.py")
    assert findings and findings[0]["kind"] == "hardcoded_account"


def test_send_keys_password_is_detected():
    text = 'driver.find_element(By.ID, "pwd").send_keys("123456")\n'
    findings = MODULE.scan_text(text, path="scripts/aiqe/per_tc/demo.py")
    assert findings and findings[0]["classification"] == "weak-default"


def test_markdown_plaintext_password_is_detected_and_blocks():
    text = "- 测试账号：运营，密码 123456\n"
    findings = MODULE.scan_text(text, path="docs/aiqe/v1.6/e2e/TC-AIQE-008-WWY-V5-001.md")
    assert findings, "Markdown 明文口令必须被识别"
    assert findings[0]["kind"] == "markdown_plaintext_password"
    assert findings[0]["classification"] == "weak-default"
    assert "123456" not in findings[0]["masked"]


def test_markdown_placeholder_text_is_not_a_finding():
    findings = MODULE.scan_text("密码不落盘，运行时由 Secret 注入\n", path="docs/x.md")
    assert findings == []


def test_authorization_bearer_cookie_and_private_key_patterns():
    cases = [
        (
            'headers = {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz123"}\n',
            "authorization_header",
        ),
        ('Cookie: "session=abcdef1234567890"\n', "cookie"),
        ('\n-----BEGIN RSA PRIVATE KEY-----\n', "private_key"),
    ]
    for text, kind in cases:
        findings = MODULE.scan_text(text, path="src/client.py")
        assert any(item["kind"] == kind for item in findings), (text, findings)


def test_url_basic_auth_and_dsn_are_detected():
    basic = MODULE.scan_text(
        "url = 'https://admin:SuperSecret123@internal.corp/api'\n", path="src/client.py"
    )
    assert any(item["kind"] == "url_basic_auth" for item in basic), basic
    dsn = MODULE.scan_text(
        "DSN = 'mysql://root:SuperSecret123@db.internal:3306/app'\n", path="src/client.py"
    )
    assert any(item["kind"] == "dsn_with_password" for item in dsn), dsn


def test_cloud_credentials_are_detected():
    azure = MODULE.scan_text(
        "DefaultEndpointsProtocol=https;AccountKey=" + "A" * 40 + "\n", path="deploy/blob.conf"
    )
    assert any(item["kind"] == "azure_storage_key" for item in azure), azure
    gcp = MODULE.scan_text(
        '{"type": "service_account", "private_key_id": "' + "0" * 40 + '"}\n',
        path="deploy/service-account.json",
    )
    assert any(item["kind"] == "gcp_private_key_id" for item in gcp), gcp
    npm = MODULE.scan_text("//registry.npmjs.org/:_authToken=npm_" + "b" * 36 + "\n", path=".npmrc")
    assert any(item["kind"] == "npm_token" for item in npm), npm


def test_test_path_findings_are_known_test_secret_not_blocking():
    findings = MODULE.scan_text(
        'page.locator(\'input[placeholder="密码"]\').fill("hardcoded-password")\n',
        path="test-platform-v2/backend/tests/test_fixture.py",
    )
    assert findings and findings[0]["classification"] == "known-test-secret"


def test_weak_default_is_never_clean():
    counts = MODULE.summarize(
        [
            {"classification": "weak-default"},
            {"classification": "potential-secret"},
        ]
    )
    assert counts["weak_default_count"] == 1
    assert counts["potential_secret_count"] == 1
    status, reasons = MODULE._status_of(counts, MODULE.summarize([]))
    assert status == "BLOCK", reasons
    assert any("weak_default_count" in reason for reason in reasons)


def test_only_known_test_secrets_stay_clean():
    counts = MODULE.summarize([{"classification": "known-test-secret"}])
    status, reasons = MODULE._status_of(counts, MODULE.summarize([]))
    assert status == "CLEAN", reasons


def test_scan_commit_sha_is_current_head():
    sha = MODULE.scan_commit_sha()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip().lower()
    assert re.fullmatch(r"[0-9a-f]{40}", sha), sha
    assert sha == head


def test_candidate_paths_include_new_and_modified_files():
    paths, _extra = MODULE._candidate_paths()
    assert "scripts/aiqe/per_tc/defect_regression_runner.py" in paths
    assert "test-platform-v2/backend/tests/test_aiqe_v162_product_status.py" in paths
    assert "scripts/aiqe/scan_credentials.py" in paths


def test_report_fields_are_complete_and_redacted():
    report = MODULE.build_report(history_limit=0)
    for field in (
        "potential_secret_count",
        "weak_default_count",
        "known_test_secret_count",
        "approved_exception_count",
        "scan_commit_sha",
        "scan_started_at",
        "scan_finished_at",
    ):
        assert field in report, field
    assert report["status"] in {"CLEAN", "BLOCK"}
    assert report["scope"]["excluded_paths"]
    assert all(item.get("reason") for item in report["scope"]["excluded_paths"])
    assert report["scope"]["scanned_file_count"] > 100
    assert re.fullmatch(r"[0-9a-f]{40}", report["scan_commit_sha"])
    assert "findings" in report
    for item in report["findings"]:
        assert set(item) <= {
            "file",
            "line",
            "kind",
            "classification",
            "masked",
            "length",
            "occurrences",
            "exception_owner",
            "exception_expires_at",
        }, item


def test_exceptions_require_owner_reason_scope_expiry_reviewer(tmp_path):
    payload = {
        "exceptions": [
            {
                "path": "src/legacy.py",
                "kind": "assigned_secret",
                "owner": "security",
                "reason": "legacy scanner fixture",
                "scope": "src/legacy.py only",
                "expires_at": "2099-01-01T00:00:00Z",
                "reviewer": "MoojinR",
            },
            {
                "path": "src/missing-reviewer.py",
                "owner": "security",
                "reason": "x",
                "scope": "x",
                "expires_at": "2099-01-01T00:00:00Z",
            },
            {
                "path": "src/expired.py",
                "owner": "security",
                "reason": "x",
                "scope": "x",
                "expires_at": "2020-01-01T00:00:00Z",
                "reviewer": "MoojinR",
            },
        ]
    }
    path = tmp_path / "exceptions.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    valid, errors = MODULE.load_exceptions(path)
    assert len(valid) == 1
    assert len(errors) == 2
    findings = MODULE.scan_text(
        'password = "hunter2-real"\n', path="src/legacy.py", exceptions=valid
    )
    assert findings and findings[0]["classification"] == "approved-exception"


# ── FIX-009：缺失 Secret 不得回退默认值 ─────────────────────
def test_credentials_only_come_from_environment_without_defaults():
    missing = REMEMBER_MODULE.resolve_credentials({})
    assert missing["available"] is False
    assert missing["missing"] == ["FUTUREWAYU_TEST_USERNAME", "FUTUREWAYU_TEST_PASSWORD"]
    partial = REMEMBER_MODULE.resolve_credentials({"FUTUREWAYU_TEST_USERNAME": "u"})
    assert partial["available"] is False
    assert partial["missing"] == ["FUTUREWAYU_TEST_PASSWORD"]
    complete = REMEMBER_MODULE.resolve_credentials(
        {"FUTUREWAYU_TEST_USERNAME": "u", "FUTUREWAYU_TEST_PASSWORD": "p"}
    )
    assert complete["available"] is True


def test_multi_end_and_overlay_share_no_default_credentials():
    assert MULTI_END_MODULE.resolve_credentials({})["available"] is False
    assert OVERLAY_MODULE.resolve_credentials({})["available"] is False
    for module in (MULTI_END_MODULE, OVERLAY_MODULE):
        text = Path(module.__file__).read_text(encoding="utf-8")
        assert "tester-operator" not in text
        assert '"123456"' not in text
