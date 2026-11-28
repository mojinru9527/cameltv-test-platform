"""V16-025 / FIX-014：独立验收记录（acceptance/records）与 GitHub Reviewer 身份校验。

默认模式保留角色域校验（兼容 70 条历史记录）；GA 模式
（``require_github_identity=True``）必须绑定真实 GitHub Review 身份。
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ACCEPTANCE = REPO_ROOT / "scripts/aiqe/acceptance_records.py"
CLI = REPO_ROOT / "scripts/aiqe/record_acceptance.py"
MATRIX = REPO_ROOT / "docs/aiqe/v1.6/traceability/requirements.yaml"
EXISTING_ARTIFACT = "docs/aiqe/v1.6/TC-010-User-Waiver.md"
SHA = "a" * 40
AUTHOR_USER_ID = 7654321
REVIEWER_USER_ID = 1234567


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


# ---------------------------------------------------------------------------
# FIX-014：真实 GitHub Reviewer 身份
# ---------------------------------------------------------------------------


def _identity_record(**overrides) -> dict:
    record = _record(
        reviewer_login="MoojinR",
        reviewer_user_id=REVIEWER_USER_ID,
        pr_number=641,
        review_id=987654321,
        reviewed_commit_sha=SHA,
        review_state="APPROVED",
        review_submitted_at="2026-11-26T10:00:00Z",
    )
    record.update(overrides)
    return record


def _ga_errors(record: dict, **kwargs):
    return MODULE.validate_record(
        record,
        requirement_id=kwargs.pop("requirement_id", "V16-001-R1"),
        owner=kwargs.pop("owner", "backend-security"),
        roles=_roles(),
        require_github_identity=True,
        expected_commit=kwargs.pop("expected_commit", SHA),
        author_user_id=kwargs.pop("author_user_id", AUTHOR_USER_ID),
        **kwargs,
    )


def test_ga_identity_record_passes():
    assert _ga_errors(_identity_record()) == []


def test_ga_rejects_reviewer_equal_to_author_user_id():
    errors = _ga_errors(_identity_record(), author_user_id=REVIEWER_USER_ID)
    assert any("同一 GitHub user id" in item for item in errors), errors


def test_ga_rejects_stale_review_commit():
    errors = _ga_errors(_identity_record(), expected_commit="f" * 40)
    assert any("stale review" in item for item in errors), errors


def test_ga_rejects_missing_review_id():
    record = _identity_record()
    record.pop("review_id")
    errors = _ga_errors(record)
    assert any("review_id" in item for item in errors), errors


def test_ga_rejects_non_approved_review_state():
    errors = _ga_errors(_identity_record(review_state="COMMENTED"))
    assert any("APPROVED" in item for item in errors), errors


def test_ga_rejects_missing_review_submitted_at():
    errors = _ga_errors(_identity_record(review_submitted_at=""))
    assert any("review_submitted_at" in item for item in errors), errors


def test_ga_requires_all_identity_fields():
    errors = _ga_errors(_record())
    for field in ("reviewer_login", "reviewer_user_id", "pr_number", "review_id", "reviewed_commit_sha"):
        assert any(field in item for item in errors), (field, errors)


def test_ga_record_without_identity_never_reviewed(tmp_path):
    """无身份字段的旧记录在 GA 模式不得进入 REVIEWED（PENDING 是预期）。"""
    (tmp_path / "V16-001-R1.json").write_text(json.dumps(_record()), encoding="utf-8")
    entries = [{"id": "V16-001-R1", "owner": "backend-security"}]
    report = MODULE.load_records(records_dir=tmp_path, entries=entries, require_github_identity=True)
    assert report.errors
    assert report.records == {}


def test_load_records_carries_identity_fields(tmp_path):
    (tmp_path / "V16-001-R1.json").write_text(json.dumps(_identity_record()), encoding="utf-8")
    entries = [{"id": "V16-001-R1", "owner": "backend-security"}]
    report = MODULE.load_records(
        records_dir=tmp_path,
        entries=entries,
        require_github_identity=True,
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )
    assert report.errors == []
    merged = MODULE.apply_records(entries, report)
    acceptance = merged[0]["acceptance"]
    assert acceptance["status"] == "REVIEWED"
    assert acceptance["reviewer_login"] == "MoojinR"
    assert acceptance["reviewer_user_id"] == REVIEWER_USER_ID
    assert acceptance["review_id"] == 987654321
    assert acceptance["reviewed_commit_sha"] == SHA
    assert acceptance["review_state"] == "APPROVED"


# ------------------------------ 在线核验（mock GitHub API） ------------------------------


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body


def _opener(payload: dict, expected_path: str = "/pulls/641/reviews/987654321"):
    def opener(request):
        assert expected_path in request.full_url, request.full_url
        return _FakeResponse(payload)

    return opener


def _online_errors(record: dict, payload: dict):
    return MODULE.validate_record(
        record,
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
        verify_online=True,
        repo="mojinru9527/cameltv-test-platform",
        # 只用于让 fetch 走到注入的 opener；不是真实令牌，也不打印。
        token="test-token-not-real",
        opener=_opener(payload),
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )


def _remote(**overrides) -> dict:
    payload = {
        "state": "APPROVED",
        "commit_id": SHA,
        "user": {"id": REVIEWER_USER_ID, "login": "MoojinR"},
    }
    payload.update(overrides)
    return payload


def test_online_identity_matching_remote_review_passes():
    assert _online_errors(_identity_record(), _remote()) == []


def test_online_identity_state_mismatch_rejected():
    errors = _online_errors(_identity_record(), _remote(state="COMMENTED"))
    assert any("REJECTED" in item and "COMMENTED" in item for item in errors), errors


def test_online_identity_commit_mismatch_rejected():
    errors = _online_errors(_identity_record(), _remote(commit_id="b" * 40))
    assert any("REJECTED" in item and "commit" in item for item in errors), errors


def test_online_identity_user_mismatch_rejected():
    errors = _online_errors(
        _identity_record(), _remote(user={"id": 42, "login": "someone-else"})
    )
    assert any("REJECTED" in item and "user id" in item for item in errors), errors
    assert any("REJECTED" in item and "login" in item for item in errors), errors


def test_online_missing_token_is_blocked_not_passed(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    errors = MODULE.validate_record(
        _identity_record(),
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
        verify_online=True,
        repo="mojinru9527/cameltv-test-platform",
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )
    assert errors
    assert any("BLOCKED" in item and "GITHUB_TOKEN" in item for item in errors), errors


# ------------------------------ GitHub 真实记录与 GA 待签状态 ------------------------------


def _matrix_entries() -> list[dict]:
    document = yaml.safe_load(MATRIX.read_text(encoding="utf-8")) or {}
    return list(document.get("requirements") or [])


def test_existing_legacy_records_load_in_default_mode():
    """70 条历史记录没有身份字段：默认模式必须保持可加载（不得批量改写）。"""
    report = MODULE.load_records(entries=_matrix_entries())
    assert report.errors == []
    assert len(report.records) == 70


def test_existing_legacy_records_pending_in_ga_mode():
    """GA 模式（release_verdict 已启用）判定 PENDING，这是预期而不是伪造通过。"""
    report = MODULE.load_records(entries=_matrix_entries(), require_github_identity=True)
    assert report.records == {}
    assert report.errors
    assert any("reviewer_login" in item for item in report.errors)


# ------------------------------ CLI（record_acceptance.py） ------------------------------


def _cli_env_without_tokens() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key not in {"GITHUB_TOKEN", "GH_TOKEN"}}


def _run_cli(args: list[str], *, env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def test_cli_ga_mode_rejects_missing_identity(tmp_path):
    result = _run_cli(
        [
            "--requirement",
            "V16-001-R1",
            "--reviewer",
            "qa-lead",
            "--reviewed-at",
            "2026-11-26",
            "--artifact",
            EXISTING_ARTIFACT,
            "--decision",
            "REVIEWED",
            "--require-github-identity",
            "--expected-commit",
            SHA,
            "--records-dir",
            str(tmp_path),
        ]
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "reviewer_login" in result.stdout
    assert not (tmp_path / "V16-001-R1.json").exists()


def test_cli_ga_mode_requires_expected_commit(tmp_path):
    """没有 --expected-commit 就无法识别 stale review，GA 模式必须拒绝。"""
    record = _identity_record()
    result = _run_cli(
        [
            "--requirement",
            "V16-001-R1",
            "--reviewer",
            "qa-lead",
            "--reviewed-at",
            "2026-11-26",
            "--artifact",
            EXISTING_ARTIFACT,
            "--decision",
            "REVIEWED",
            "--reviewer-login",
            record["reviewer_login"],
            "--reviewer-user-id",
            str(record["reviewer_user_id"]),
            "--pr-number",
            str(record["pr_number"]),
            "--review-id",
            str(record["review_id"]),
            "--reviewed-commit-sha",
            SHA,
            "--review-state",
            "APPROVED",
            "--review-submitted-at",
            record["review_submitted_at"],
            "--require-github-identity",
            "--records-dir",
            str(tmp_path),
        ]
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "--expected-commit" in result.stdout
    assert not (tmp_path / "V16-001-R1.json").exists()


def test_cli_ga_mode_writes_identity_fields(tmp_path):
    result = _run_cli(
        [
            "--requirement",
            "V16-001-R1",
            "--reviewer",
            "qa-lead",
            "--reviewed-at",
            "2026-11-26",
            "--artifact",
            EXISTING_ARTIFACT,
            "--decision",
            "REVIEWED",
            "--reviewer-login",
            "MoojinR",
            "--reviewer-user-id",
            str(REVIEWER_USER_ID),
            "--pr-number",
            "641",
            "--review-id",
            "987654321",
            "--reviewed-commit-sha",
            SHA,
            "--review-state",
            "APPROVED",
            "--review-submitted-at",
            "2026-11-26T10:00:00Z",
            "--require-github-identity",
            "--expected-commit",
            SHA,
            "--author-user-id",
            str(AUTHOR_USER_ID),
            "--records-dir",
            str(tmp_path),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads((tmp_path / "V16-001-R1.json").read_text(encoding="utf-8"))
    assert payload["reviewer_login"] == "MoojinR"
    assert payload["reviewer_user_id"] == REVIEWER_USER_ID
    assert payload["review_id"] == 987654321
    assert payload["review_state"] == "APPROVED"
    assert payload["reviewed_commit_sha"] == SHA
    assert payload["review_submitted_at"] == "2026-11-26T10:00:00Z"


def test_cli_online_verification_without_token_is_blocked(tmp_path):
    result = _run_cli(
        [
            "--requirement",
            "V16-001-R1",
            "--reviewer",
            "qa-lead",
            "--reviewed-at",
            "2026-11-26",
            "--artifact",
            EXISTING_ARTIFACT,
            "--decision",
            "REVIEWED",
            "--reviewer-login",
            "MoojinR",
            "--reviewer-user-id",
            str(REVIEWER_USER_ID),
            "--pr-number",
            "641",
            "--review-id",
            "987654321",
            "--reviewed-commit-sha",
            SHA,
            "--review-state",
            "APPROVED",
            "--review-submitted-at",
            "2026-11-26T10:00:00Z",
            "--verify-online",
            "--expected-commit",
            SHA,
            "--records-dir",
            str(tmp_path),
        ],
        env=_cli_env_without_tokens(),
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BLOCKED" in result.stdout
    assert not (tmp_path / "V16-001-R1.json").exists()
