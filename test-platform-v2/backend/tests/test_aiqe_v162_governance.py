"""FIX-013 / FIX-014 治理整改集成测试。

FIX-013：AIQE 专项聚合门禁纳入 Main Ruleset
- ``check_branch_protection.py --check`` 精确校验 4 个 required context（含
  ``AIQE V1.6 Governance Gate``），不能“非空即通过”；
- ``--capture`` 记录 ruleset 明细、来源 App、API 快照、采集时间与仓库/Ruleset ID；
- ``update_branch_protection.py`` 幂等追加缺失 context，dry-run 不写线上；
- ``.github/workflows/aiqe-v16-gates.yml`` 提供稳定 Aggregate Job，
  逐项检查 needs，skip 不得当 PASS，PR 不得伪造产品 E2E PASS。

FIX-014：验收记录绑定真实 GitHub Reviewer 身份
- 同 GitHub user id / stale commit / 缺 review id / 非 APPROVED 必须拒绝；
- 在线核验匹配通过、不匹配拒绝、无法回查 BLOCKED；
- 旧角色域记录默认模式仍可加载（70 条历史记录不伪造身份）。
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
SCRIPTS = REPO_ROOT / "scripts/aiqe"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/aiqe-v16-gates.yml"
CHECK_BRANCH_PROTECTION = SCRIPTS / "check_branch_protection.py"
UPDATE_BRANCH_PROTECTION = SCRIPTS / "update_branch_protection.py"
ACCEPTANCE_RECORDS = SCRIPTS / "acceptance_records.py"

SHA = "a" * 40
RULESET_ID = 18351498
GITHUB_ACTIONS_APP_ID = 15368
AUTHOR_USER_ID = 7654321
REVIEWER_USER_ID = 1234567
EXISTING_ARTIFACT = "docs/aiqe/v1.6/TC-010-User-Waiver.md"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


CHECK = _load("governance_check_branch_protection", CHECK_BRANCH_PROTECTION)
UPDATE = _load("governance_update_branch_protection", UPDATE_BRANCH_PROTECTION)
ACCEPTANCE = _load("governance_acceptance_records", ACCEPTANCE_RECORDS)

WORKFLOW = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
JOBS = WORKFLOW["jobs"]


def _validators():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from validators import acceptance as acceptance_validator
    from validators import branch as branch_validator

    return branch_validator, acceptance_validator


def _on_block() -> dict:
    for key in ("on", True):
        if key in WORKFLOW:
            return WORKFLOW[key]
    return {}


# ===========================================================================
# FIX-013：精确 required checks
# ===========================================================================


def test_required_checks_are_the_exact_four_contexts():
    branch_validator, _ = _validators()
    assert branch_validator.AIQE_AGGREGATE_CHECK == "AIQE V1.6 Governance Gate"
    assert branch_validator.REQUIRED_CHECKS == (
        "后端全新检出与全量回归",
        "前端全新检出与全量回归",
        "AI/Git 交付策略",
        "AIQE V1.6 Governance Gate",
    )
    assert branch_validator.TRUSTED_APPS == {GITHUB_ACTIONS_APP_ID}


def _payload(branch_validator, **overrides):
    checks = list(branch_validator.REQUIRED_CHECKS)
    payload = {
        "verified": True,
        "source": "github-api",
        "required_checks": checks,
        "require_pr_before_merge": True,
        "require_non_author_review": True,
        "allow_force_push": False,
        "allow_deletions": False,
        "checked_at": "2026-11-28T00:00:00+00:00",
        "ruleset_ids": [RULESET_ID],
        "rulesets": [
            {
                "id": RULESET_ID,
                "name": "protect-main",
                "rules": [
                    {"type": "deletion"},
                    {"type": "non_fast_forward"},
                    {
                        "type": "pull_request",
                        "parameters": {
                            "require_code_owner_review": True,
                            "required_approving_review_count": 1,
                        },
                    },
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [
                                {"context": name, "integration_id": GITHUB_ACTIONS_APP_ID}
                                for name in checks
                            ]
                        },
                    },
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_check_requires_exact_aiqe_context():
    branch_validator, _ = _validators()
    checks = list(branch_validator.REQUIRED_CHECKS)
    missing_aiqe = _payload(
        branch_validator,
        required_checks=checks[:3],
        rulesets=[
            {
                "id": RULESET_ID,
                "name": "protect-main",
                "rules": [
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [
                                {"context": name, "integration_id": GITHUB_ACTIONS_APP_ID}
                                for name in checks[:3]
                            ]
                        },
                    }
                ],
            }
        ],
    )
    errors = CHECK.validate(missing_aiqe)
    assert any(branch_validator.AIQE_AGGREGATE_CHECK in item for item in errors), errors

    extra = _payload(branch_validator, required_checks=checks + ["额外观察检查"])
    assert CHECK.validate(extra) == []


# ===========================================================================
# FIX-013：--capture 证据结构与来源 App
# ===========================================================================


def _fake_capture_api(branch_validator, *, aiqe_app_id: int = GITHUB_ACTIONS_APP_ID):
    checks = list(branch_validator.REQUIRED_CHECKS)

    def fake_request(path: str, token: str):
        assert token
        aiqe_check = branch_validator.AIQE_AGGREGATE_CHECK

        if path.endswith("/protection"):
            return 404, {}
        if "/rulesets?targets=branch" in path:
            return 200, [
                {"id": RULESET_ID, "name": "protect-main", "enforcement": "active", "target": "branch"}
            ]
        if path.endswith(f"/rulesets/{RULESET_ID}"):
            return 200, {
                "id": RULESET_ID,
                "name": "protect-main",
                "enforcement": "active",
                "target": "branch",
                "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                "rules": [
                    {"type": "deletion"},
                    {"type": "non_fast_forward"},
                    {
                        "type": "pull_request",
                        "parameters": {
                            "require_code_owner_review": True,
                            "required_approving_review_count": 1,
                        },
                    },
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [
                                {
                                    "context": name,
                                    "integration_id": (
                                        aiqe_app_id if name == aiqe_check else GITHUB_ACTIONS_APP_ID
                                    ),
                                }
                                for name in checks
                            ]
                        },
                    },
                ],
            }
        if "/check-runs" in path:
            return 200, {
                "total_count": len(checks),
                "check_runs": [
                    {
                        "name": name,
                        "app": {"id": aiqe_app_id, "slug": "untrusted-app"},
                        "status": "completed",
                        "conclusion": "success",
                        "head_sha": SHA,
                    }
                    for name in checks
                ],
            }
        raise AssertionError(f"unexpected API path: {path}")

    return fake_request


def test_capture_records_ruleset_detail_sources_and_snapshot(monkeypatch):
    branch_validator, _ = _validators()
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token-not-real")
    monkeypatch.setattr(CHECK, "_request", _fake_capture_api(branch_validator))
    payload = CHECK.capture("mojinru9527/cameltv-test-platform", "main")

    assert payload["verified"] is True
    assert payload["checked_at"] and payload["captured_at"] == payload["checked_at"]
    assert payload["repository"] == "mojinru9527/cameltv-test-platform"
    assert payload["ruleset_ids"] == [RULESET_ID]
    assert set(branch_validator.REQUIRED_CHECKS) <= set(payload["required_checks"])

    details = {item["context"]: item for item in payload["required_checks_detail"]}
    aiqe = details[branch_validator.AIQE_AGGREGATE_CHECK]
    assert aiqe["integration_id"] == GITHUB_ACTIONS_APP_ID
    assert aiqe["ruleset_id"] == RULESET_ID

    sources = payload["check_sources"]
    assert sources[branch_validator.AIQE_AGGREGATE_CHECK]["app_id"] == GITHUB_ACTIONS_APP_ID

    snapshot = payload["ruleset_api_snapshot"]
    assert snapshot["captured_at"] == payload["captured_at"]
    assert snapshot["repository"] == payload["repository"]
    assert snapshot["ruleset_ids"] == [RULESET_ID]
    assert str(RULESET_ID) in snapshot["ruleset_details"]
    assert CHECK.validate(payload) == []


def test_capture_requires_token(monkeypatch):
    branch_validator, _ = _validators()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    try:
        CHECK.capture("mojinru9527/cameltv-test-platform", "main")
    except CHECK.CaptureError as exc:
        assert "GITHUB_TOKEN" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("缺少 token 时必须 CaptureError，不能伪装成功")


def test_capture_untrusted_check_source_rejected(monkeypatch):
    branch_validator, _ = _validators()
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token-not-real")
    monkeypatch.setattr(CHECK, "_request", _fake_capture_api(branch_validator, aiqe_app_id=424242))
    payload = CHECK.capture("mojinru9527/cameltv-test-platform", "main")
    errors = CHECK.validate(payload)
    assert any("不可信" in item for item in errors), errors


def test_capture_cli_writes_evidence(monkeypatch, tmp_path):
    branch_validator, _ = _validators()
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token-not-real")
    monkeypatch.setattr(CHECK, "_request", _fake_capture_api(branch_validator))
    target = tmp_path / "branch-protection.json"
    assert CHECK.main(["--capture", "--target", str(target)]) == 0
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["ruleset_ids"] == [RULESET_ID]


# ===========================================================================
# FIX-013：update_branch_protection 幂等且 dry-run 不写线上
# ===========================================================================


def _fake_update_api(branch_validator, calls: list[tuple[str, str]]):
    checks = list(branch_validator.REQUIRED_CHECKS)

    def fake_request(method: str, path: str, token: str, payload: dict | None = None):
        calls.append((method, path))
        assert token
        if path.endswith("/collaborators"):
            return 200, [{"login": "mojinru9527"}, {"login": "qa-reviewer"}]
        if path.endswith("/permission"):
            return 200, {"permission": "admin"}
        if path.endswith(f"/rulesets/{RULESET_ID}"):
            return 200, {
                "id": RULESET_ID,
                "name": "protect-main",
                "enforcement": "active",
                "target": "branch",
                "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                "rules": [
                    {"type": "deletion"},
                    {"type": "non_fast_forward"},
                    {
                        "type": "pull_request",
                        "parameters": {
                            "require_code_owner_review": True,
                            "required_approving_review_count": 1,
                        },
                    },
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [
                                {"context": name, "integration_id": GITHUB_ACTIONS_APP_ID}
                                for name in checks[:3]
                            ]
                        },
                    },
                ],
            }
        raise AssertionError(f"unexpected API call: {method} {path}")

    return fake_request


def test_update_dry_run_appends_aiqe_check_without_put(monkeypatch, capsys):
    branch_validator, _ = _validators()
    calls: list[tuple[str, str]] = []
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token-not-real")
    monkeypatch.setattr(UPDATE, "_request", _fake_update_api(branch_validator, calls))

    assert UPDATE.main(["--reviewer-login", "qa-reviewer", "--ensure-required-checks"]) == 0
    output = capsys.readouterr().out
    assert "required_checks before:" in output
    assert "required_checks after:" in output
    assert branch_validator.AIQE_AGGREGATE_CHECK in output
    assert "required_checks added:" in output
    # dry-run 绝不能发出 PUT（不得修改线上 Ruleset）
    assert all(method != "PUT" for method, _ in calls), calls


# ===========================================================================
# FIX-013：Workflow Aggregate Gate 契约
# ===========================================================================


def _aggregate_script() -> str:
    step = next(
        item
        for item in JOBS["aiqe-aggregate"]["steps"]
        if item.get("name") == "Aggregate required gate results"
    )
    run = step["run"]
    return run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


def _run_aggregate(needs: dict, *, release_context: bool) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["NEEDS_JSON"] = json.dumps(needs)
    env["RELEASE_CONTEXT"] = "true" if release_context else "false"
    return subprocess.run(
        [sys.executable, "-c", _aggregate_script()],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _needs(**overrides) -> dict:
    needs = {
        job: {"result": "success"}
        for job in (
            "traceability",
            "lint-type",
            "unit-integration",
            "runtime-security",
            "migration",
        )
    }
    needs.update(overrides)
    return needs


def test_workflow_has_stable_aggregate_job_name():
    branch_validator, _ = _validators()
    aggregate = JOBS["aiqe-aggregate"]
    assert aggregate["name"] == branch_validator.AIQE_AGGREGATE_CHECK
    assert set(aggregate["needs"]) == {
        "traceability",
        "lint-type",
        "unit-integration",
        "runtime-security",
        "migration",
        "release-gate",
    }
    assert aggregate.get("if") == "${{ always() }}"


def test_existing_job_names_not_changed():
    expected = {
        "traceability": "Traceability Gate",
        "lint-type": "Build & Quality Gate",
        "unit-integration": "Unit / Integration Gate",
        "runtime-security": "Runtime / Negative Security Gate",
        "migration": "Migration Gate",
        "release-gate": "Release Gate (GA verdict)",
    }
    for job_id, name in expected.items():
        assert JOBS[job_id]["name"] == name, (job_id, JOBS[job_id]["name"])


def test_release_gate_waits_for_artifact_jobs():
    """证据清单依赖其他 gate 的 JUnit/runtime artifact，release-gate 必须先等它们完成。"""
    assert set(JOBS["release-gate"]["needs"]) == {
        "traceability",
        "lint-type",
        "unit-integration",
        "runtime-security",
        "migration",
    }


def test_workflow_triggers_unchanged():
    triggers = _on_block()
    assert triggers["pull_request"]["branches"] == ["main", "release/**"]
    assert triggers["push"]["tags"] == ["aiqe-v*"]
    assert "workflow_dispatch" in triggers


def test_aggregate_pr_pass_marks_release_gate_skipped_and_product_not_run():
    result = _run_aggregate(_needs(**{"release-gate": {"result": "skipped"}}), release_context=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "release_gate=SKIPPED(PR)" in result.stdout
    assert "product_e2e=NOT_RUN" in result.stdout
    assert "ga_ready=false" in result.stdout
    assert "产品 TC 全部通过" not in result.stdout


def test_aggregate_failure_in_any_required_job_fails():
    needs = _needs()
    needs["unit-integration"] = {"result": "failure"}
    needs["release-gate"] = {"result": "skipped"}
    result = _run_aggregate(needs, release_context=False)
    assert result.returncode == 1
    assert "unit-integration=FAILURE" in result.stdout


def test_aggregate_cancelled_job_fails():
    needs = _needs()
    needs["runtime-security"] = {"result": "cancelled"}
    needs["release-gate"] = {"result": "skipped"}
    result = _run_aggregate(needs, release_context=False)
    assert result.returncode == 1
    assert "runtime-security=CANCELLED" in result.stdout


def test_aggregate_missing_job_result_fails():
    needs = _needs()
    needs.pop("migration")
    needs["release-gate"] = {"result": "skipped"}
    result = _run_aggregate(needs, release_context=False)
    assert result.returncode == 1
    assert "migration=MISSING" in result.stdout


def test_aggregate_release_gate_skipped_on_release_fails():
    needs = _needs(**{"release-gate": {"result": "skipped"}})
    result = _run_aggregate(needs, release_context=True)
    assert result.returncode == 1
    assert "release_gate=SKIPPED_BUT_REQUIRED" in result.stdout
    assert "ga_ready=false" in result.stdout


def test_aggregate_release_success_reports_ga_ready():
    needs = _needs(**{"release-gate": {"result": "success"}})
    result = _run_aggregate(needs, release_context=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ga_ready=true" in result.stdout


def test_release_gate_runs_product_tc_with_guard_but_not_on_pr():
    release_steps = JOBS["release-gate"]["steps"]
    product_steps = [
        step
        for step in release_steps
        if "python scripts/aiqe/run_product_tc.py --run" in step.get("run", "")
    ]
    assert len(product_steps) == 1
    step = product_steps[0]
    assert "refs/tags/aiqe-v" in step.get("if", "")
    assert "release/" in step.get("if", "")
    script = step["run"]
    assert "python scripts/aiqe/run_product_tc.py --run" in script
    assert "verify_product_tc_results.py --require-pass" in script
    assert "[ ! -f scripts/aiqe/run_product_tc.py ]" in script
    assert "[ ! -f scripts/aiqe/verify_product_tc_results.py ]" in script
    assert "exit 1" in script
    # 整个 workflow 中产品 TC 只在 release/tag 条件步骤执行，PR 不得伪造 PASS。
    for job in JOBS.values():
        for item in job.get("steps", []):
            if "python scripts/aiqe/run_product_tc.py --run" in item.get("run", ""):
                assert "refs/tags/aiqe-v" in item.get("if", ""), item


def test_runtime_evidence_index_uses_artifact_sha_as_source_of_truth():
    """FIX-011：platform-results.json 自带 tested_commit_sha 是事实源。

    PR 的 checkout 是 merge ref（github.sha），不能拿 head SHA 覆盖 artifact；
    因此 builder 不再接收 --commit-sha，PR head / merge commit 分字段记录。
    """
    unit_steps = JOBS["unit-integration"]["steps"]
    step = next(
        item for item in unit_steps if "build_evidence_index.py" in item.get("run", "")
    )
    script = step["run"]
    assert "--commit-sha" not in script
    assert "--pr-head-sha" in script
    assert "github.event.pull_request.head.sha || ''" in script
    assert "--merge-commit-sha" in script and '"${{ github.sha }}"' in script
    assert '--workflow-attempt "${{ github.run_attempt }}"' in script
    assert '--job-id "${{ github.job }}"' in script
    assert "--runtime-type host" in script
    assert "--require-tcs 10" in script
    # 平台负向用例 BLOCKED 属正常证据，不加 --fail-on-blocked；也不得伪造 ga_ready。
    assert "--fail-on-blocked" not in script


def test_evidence_manifest_wired_for_pr_and_ga():
    aggregate_steps = JOBS["aiqe-aggregate"]["steps"]
    pr_step = next(
        step for step in aggregate_steps if "build_evidence_manifest.py" in step.get("run", "")
    )
    pr_script = pr_step["run"]
    assert "--commit-sha" in pr_script and "--workflow-run-id" in pr_script
    assert "--environment" in pr_script
    assert "evidence-manifest.json" in pr_script and "evidence-manifest.md" in pr_script
    # PR 场景不得 --require-complete（JUnit 等 artifact 可能尚未生成）
    assert "--require-complete" not in pr_script

    ga_step = next(
        step
        for step in JOBS["release-gate"]["steps"]
        if "build_evidence_manifest.py" in step.get("run", "")
    )
    assert "--require-complete" in ga_step["run"]

    artifact_paths = "\n".join(
        str(step.get("with", {}).get("path", ""))
        for step in list(aggregate_steps) + list(JOBS["release-gate"]["steps"])
        if str(step.get("uses", "")).startswith("actions/upload-artifact")
    )
    assert "evidence-manifest.json" in artifact_paths
    assert "evidence-manifest.md" in artifact_paths


# ===========================================================================
# FIX-014：验收记录绑定真实 GitHub Reviewer 身份
# ===========================================================================


def _roles() -> dict:
    return ACCEPTANCE.load_role_matrix()


def _identity_record(**overrides) -> dict:
    record = {
        "requirement_id": "V16-001-R1",
        "decision": "REVIEWED",
        "reviewer": "qa-lead",
        "reviewed_at": "2026-11-26",
        "review_submitted_at": "2026-11-26T10:00:00Z",
        "artifact": EXISTING_ARTIFACT,
        "reviewer_login": "MoojinR",
        "reviewer_user_id": REVIEWER_USER_ID,
        "pr_number": 641,
        "review_id": 987654321,
        "reviewed_commit_sha": SHA,
        "review_state": "APPROVED",
    }
    record.update(overrides)
    return record


def _ga_errors(record: dict) -> list[str]:
    return ACCEPTANCE.validate_record(
        record,
        requirement_id=str(record.get("requirement_id") or "V16-001-R1"),
        owner="backend-security",
        roles=_roles(),
        require_github_identity=True,
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )


def test_ga_identity_record_accepted():
    assert _ga_errors(_identity_record()) == []


def test_ga_rejects_same_github_user_id():
    errors = _ga_errors(_identity_record())
    assert errors == []
    same = ACCEPTANCE.validate_record(
        _identity_record(),
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
        require_github_identity=True,
        expected_commit=SHA,
        author_user_id=REVIEWER_USER_ID,
    )
    assert any("同一 GitHub user id" in item for item in same), same


def test_ga_rejects_stale_review_sha():
    errors = ACCEPTANCE.validate_record(
        _identity_record(),
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
        require_github_identity=True,
        expected_commit="f" * 40,
        author_user_id=AUTHOR_USER_ID,
    )
    assert any("stale review" in item for item in errors), errors


def test_ga_rejects_missing_review_id():
    record = _identity_record()
    record.pop("review_id")
    errors = _ga_errors(record)
    assert any("review_id" in item for item in errors), errors


def test_ga_rejects_non_approved_review():
    errors = _ga_errors(_identity_record(review_state="CHANGES_REQUESTED"))
    assert any("APPROVED" in item for item in errors), errors


def test_legacy_role_records_still_load_by_default():
    legacy = {
        "requirement_id": "V16-001-R1",
        "decision": "REVIEWED",
        "reviewer": "qa-lead",
        "reviewed_at": "2026-11-24",
        "artifact": EXISTING_ARTIFACT,
    }
    assert (
        ACCEPTANCE.validate_record(
            legacy, requirement_id="V16-001-R1", owner="backend-security", roles=_roles()
        )
        == []
    )
    assert ACCEPTANCE.validate_record(
        legacy,
        requirement_id="V16-001-R1",
        owner="backend-security",
        roles=_roles(),
        require_github_identity=False,
    ) == []


def test_online_verification_matching_review_passes(monkeypatch):
    _, acceptance_validator = _validators()
    monkeypatch.setattr(
        acceptance_validator,
        "fetch_github_review",
        lambda *args, **kwargs: {
            "state": "APPROVED",
            "commit_id": SHA,
            "user": {"id": REVIEWER_USER_ID, "login": "MoojinR"},
        },
    )
    check = acceptance_validator.verify_github_identity(
        _identity_record(),
        repo="mojinru9527/cameltv-test-platform",
        token="dummy-token-not-real",
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )
    assert check.status == "PASS", check.as_dict()


def test_online_verification_state_mismatch_rejected(monkeypatch):
    _, acceptance_validator = _validators()
    monkeypatch.setattr(
        acceptance_validator,
        "fetch_github_review",
        lambda *args, **kwargs: {
            "state": "CHANGES_REQUESTED",
            "commit_id": SHA,
            "user": {"id": REVIEWER_USER_ID, "login": "MoojinR"},
        },
    )
    check = acceptance_validator.verify_github_identity(
        _identity_record(),
        repo="mojinru9527/cameltv-test-platform",
        token="dummy-token-not-real",
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )
    assert check.status != "PASS"
    assert any("实际状态" in item for item in check.reasons), check.reasons


def test_online_verification_commit_and_user_mismatch_rejected(monkeypatch):
    _, acceptance_validator = _validators()
    monkeypatch.setattr(
        acceptance_validator,
        "fetch_github_review",
        lambda *args, **kwargs: {
            "state": "APPROVED",
            "commit_id": "b" * 40,
            "user": {"id": 424242, "login": "someone-else"},
        },
    )
    check = acceptance_validator.verify_github_identity(
        _identity_record(),
        repo="mojinru9527/cameltv-test-platform",
        token="dummy-token-not-real",
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )
    assert check.status != "PASS"
    reasons = " ".join(check.reasons)
    assert "commit" in reasons
    assert "user id" in reasons
    assert "login" in reasons


def test_online_verification_without_token_is_blocked_not_passed(monkeypatch):
    _, acceptance_validator = _validators()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    check = acceptance_validator.verify_github_identity(
        _identity_record(),
        repo="mojinru9527/cameltv-test-platform",
        expected_commit=SHA,
        author_user_id=AUTHOR_USER_ID,
    )
    assert check.status != "PASS"
    assert any("GITHUB_TOKEN" in item for item in check.reasons), check.reasons
