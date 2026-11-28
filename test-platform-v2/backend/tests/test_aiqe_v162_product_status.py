"""V1.6.2 FIX-007/008/010：多端状态、Defect 回归、生产阶段语义的正/反向测试。

覆盖：
- FIX-007：截图/半自动不得折算 PASS；多端按 mandatory 平台最弱覆盖聚合；伪造 PASS 被拒绝；
- FIX-008：正式 Defect Regression 校验链（固定 SHA / scope 全覆盖 / mandatory case 结果 /
  Comparison Snapshot），另一条用例不能改变原缺陷状态；
- FIX-010：跳过后 PASS、缺批准人/到期时间的 WAIVED、只有回滚命令的 drill 均不得 PASS；
  仓库内 production-evidence.json 与 Gate F 必须非 PASS。
"""
from __future__ import annotations

import importlib.util
import json
import re
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AIQE_DIR = REPO_ROOT / "scripts/aiqe"
if str(AIQE_DIR) not in sys.path:
    sys.path.insert(0, str(AIQE_DIR))

SHA = "a" * 40
OTHER_SHA = "d" * 40
DIGEST = "sha256:" + "b" * 64
CANARY = "docs/aiqe/v1.6/evidence/production-stage-canary-eb20.json"
PRODUCTION_EVIDENCE = REPO_ROOT / "docs/aiqe/v1.6/governance/production-evidence.json"
MULTI_END_SCRIPT = AIQE_DIR / "per_tc/futurewayu_multi_end.py"
REMEMBER_SCRIPT = AIQE_DIR / "per_tc/futurewayu_remember_account.py"
REGRESSION_SCRIPT = AIQE_DIR / "per_tc/defect_regression_runner.py"
RELEASE_VERDICT_SCRIPT = AIQE_DIR / "release_verdict.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MULTI_END = _load("vw162_multi_end", MULTI_END_SCRIPT)
REMEMBER = _load("vw162_remember_account", REMEMBER_SCRIPT)
REGRESSION = _load("vw162_defect_regression", REGRESSION_SCRIPT)
PRODUCTION = _load("vw162_production_validator", AIQE_DIR / "validators/production.py")
RELEASE_VERDICT = _load("vw162_release_verdict", RELEASE_VERDICT_SCRIPT)


def _run_script(script: Path, args: list[str], *, env: dict | None = None) -> subprocess.CompletedProcess:
    import os

    merged = dict(os.environ)
    merged["PYTHONIOENCODING"] = "utf-8"
    merged.pop("FUTUREWAYU_TEST_USERNAME", None)
    merged.pop("FUTUREWAYU_TEST_PASSWORD", None)
    merged.update(env or {})
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        env=merged,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


# ────────────────────────── FIX-007：多端状态 ──────────────────────────
def _desktop_evidence(**overrides) -> dict:
    raw = {
        "executed": True,
        "automation_mode": "playwright",
        "business_navigation": {
            "url": "https://xinyuwadao.com/dashboard",
            "title": "工作台",
            "page_marker": "工作台",
        },
        "key_interactions": [{"action": "login"}, {"action": "open_business_menu"}],
        "business_assertions": [
            {"name": "login_redirected", "passed": True},
            {"name": "business_menu_visible", "passed": True},
        ],
        "identity": {"executed_as": "secret:FUTUREWAYU_TEST_USERNAME"},
        "build_version": {"app_version": "v5.0.1"},
        "artifacts": ["docs/aiqe/v1.6/evidence/product/TC-AIQE-009/desktop-business.png"],
    }
    raw.update(overrides)
    return raw


def _android_evidence(**overrides) -> dict:
    raw = _desktop_evidence(
        automation_mode="appium",
        business_navigation={
            "url": "android://uni.app.UNIE3747D0/io.dcloud.PandoraEntryActivity",
            "title": "OnePlus6T / Android 13",
            "page_marker": "首页",
        },
        identity={"executed_as": "secret:FUTUREWAYU_ANDROID_ACCOUNT_SECRET"},
        build_version={"app_version": "5.0.1"},
    )
    raw.update(overrides)
    return raw


def _wechat_complete(**overrides) -> dict:
    raw = {
        "executed": True,
        "automation_mode": "controlled_device",
        "business_navigation": {
            "url": "weixin://miniapp/futurewayu/home",
            "title": "未来娃屿",
            "page_marker": "首页",
        },
        "key_interactions": [{"action": "open_miniapp"}, {"action": "tap_store_tab"}],
        "business_assertions": [{"name": "home_visible", "passed": True}],
        "identity": {"executed_as": "secret:FUTUREWAYU_TEST_USERNAME"},
        "build_version": {"app_version": "5.0.1"},
        "artifacts": ["docs/aiqe/v1.6/evidence/product/TC-AIQE-009/wechat-device.mp4"],
    }
    raw.update(overrides)
    return raw


def test_f7_wechat_screenshot_only_is_partial():
    result = MULTI_END.evaluate_platform(
        "wechat_miniapp",
        {"executed": True, "automation_mode": "screenshot_copy", "artifacts": ["wechat.png"]},
    )
    assert result["status"] == "PARTIAL", result
    assert result["uncovered"], "PARTIAL 必须写明未覆盖范围"
    legacy_shape = MULTI_END.evaluate_platform(
        "wechat_miniapp", {"executed": True, "screenshot": "wechat-panel.png"}
    )
    assert legacy_shape["status"] == "PARTIAL", legacy_shape


def test_f7_page_without_business_assertions_is_not_proven():
    no_assertion = MULTI_END.evaluate_platform(
        "desktop", _desktop_evidence(business_assertions=[])
    )
    assert no_assertion["status"] == "NOT_PROVEN", no_assertion
    no_navigation = MULTI_END.evaluate_platform(
        "desktop",
        {"executed": True, "automation_mode": "playwright", "artifacts": ["login.png"]},
    )
    assert no_navigation["status"] == "NOT_PROVEN", no_navigation


def test_f7_legacy_semi_automatic_maps_to_partial_never_pass():
    result = MULTI_END.evaluate_platform(
        "wechat_miniapp",
        {"executed": True, "legacy_status": "SEMI_AUTOMATIC", "artifacts": ["panel.png"]},
    )
    assert result["status"] == "PARTIAL", result
    assert result["status"] != "PASS"


def test_f7_http_200_and_screenshot_alone_cannot_pass():
    result = MULTI_END.evaluate_platform(
        "desktop",
        {
            "executed": True,
            "automation_mode": "playwright",
            "http_status": 200,
            "screenshot": "login.png",
        },
    )
    assert result["status"] != "PASS", result


def test_f7_identity_and_version_are_required_for_pass():
    missing_identity = MULTI_END.evaluate_platform(
        "desktop", _desktop_evidence(identity={})
    )
    assert missing_identity["status"] == "NOT_PROVEN", missing_identity
    missing_version = MULTI_END.evaluate_platform(
        "desktop", _desktop_evidence(build_version={})
    )
    assert missing_version["status"] == "NOT_PROVEN", missing_version


def test_f7_failed_business_assertion_is_fail():
    result = MULTI_END.evaluate_platform(
        "desktop",
        _desktop_evidence(business_assertions=[{"name": "menu_visible", "passed": False}]),
    )
    assert result["status"] == "FAIL", result


def test_f7_all_platforms_pass_only_with_complete_evidence():
    aggregated = MULTI_END.aggregate_multi_end(
        {
            "desktop": _desktop_evidence(),
            "android": _android_evidence(),
            "wechat_miniapp": _wechat_complete(),
        }
    )
    assert aggregated["status"] == "PASS", aggregated
    assert MULTI_END.exit_code(aggregated["status"]) == 0


def test_f7_android_pass_wechat_blocked_overall_not_pass():
    aggregated = MULTI_END.aggregate_multi_end(
        {
            "desktop": _desktop_evidence(),
            "android": _android_evidence(),
            "wechat_miniapp": {"blocked_reason": "无开发者权限/设备池不可用"},
        }
    )
    assert aggregated["status"] in {"PARTIAL", "BLOCKED"}, aggregated
    assert aggregated["status"] != "PASS"
    assert MULTI_END.exit_code(aggregated["status"]) == 1
    assert any(
        item["platform"] == "wechat_miniapp" for item in aggregated["uncovered_scope"]
    )


def test_f7_missing_mandatory_platform_record_cannot_pass():
    aggregated = MULTI_END.aggregate_multi_end(
        {"desktop": _desktop_evidence(), "android": _android_evidence()}
    )
    assert aggregated["status"] != "PASS", aggregated


def test_f7_forged_partial_as_pass_is_rejected():
    platforms = {
        name: {"executed": True, "automation_mode": "screenshot_copy", "artifacts": ["x.png"]}
        for name in MULTI_END.MANDATORY_PLATFORMS
    }
    validation = MULTI_END.validate_multi_end_result({"status": "PASS", "platforms": platforms})
    assert validation["forged_pass_rejected"] is True, validation
    assert validation["status"] == "PARTIAL", validation
    assert MULTI_END.exit_code(validation["status"]) == 1


def test_f7_no_per_tc_script_treats_legacy_status_as_success():
    for path in sorted((AIQE_DIR / "per_tc").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\{\s*[\"']PASS[\"']\s*,\s*[\"']SEMI_AUTOMATIC", text), path
        assert 'PASS", "SEMI_AUTOMATIC' not in text, path


def test_f7_missing_secret_makes_runner_blocked_without_defaults(tmp_path):
    result = _run_script(
        MULTI_END_SCRIPT,
        ["--out-dir", str(tmp_path), "--skip-android"],
    )
    assert result.returncode != 0, result.stdout + result.stderr
    payload = json.loads((tmp_path / "multi-end.json").read_text(encoding="utf-8"))
    assert payload["credential_available"] is False
    assert payload["status"] != "PASS"
    desktop = payload["platform_evidence"]["desktop"]
    assert "FUTUREWAYU_TEST_PASSWORD" in desktop["blocked_reason"]
    assert payload["platforms"]["desktop"]["status"] == "BLOCKED"
    assert "123456" not in json.dumps(payload, ensure_ascii=False)


# ────────────────────────── FIX-008：Defect 回归 ──────────────────────────
DEFECT_ID = 42
MANDATORY_CASES = [f"TC-CASE-{index}" for index in range(1, 6)]


def _scope() -> dict:
    return {
        "snapshot_id": "scope-wwy-v5-001",
        "checksum_sha256": "c" * 64,
        "mandatory_case_ids": list(MANDATORY_CASES),
    }


def _case_results(count: int = 5) -> list[dict]:
    return [
        {"case_id": case, "status": "PASS", "assertion_ids": [f"assert-{case}"]}
        for case in MANDATORY_CASES[:count]
    ]


def _regression_payload(**overrides) -> dict:
    payload = {
        "regression": {
            "id": 7,
            "defect_id": DEFECT_ID,
            "fixed_sha": SHA,
            "status": "PASS",
            "blocked": False,
            "mandatory_case_ids": list(MANDATORY_CASES),
        },
        "comparison": {
            "available": True,
            "snapshot": {"fixed_sha": SHA, "outcome": "PASS", "new_failures": []},
        },
        "mandatory_case_results": _case_results(),
    }
    payload.update(overrides)
    return payload


def _validate_regression(payload: dict, **overrides):
    kwargs = {
        "defect_id": DEFECT_ID,
        "fixed_commit_sha": SHA,
        "mandatory_case_ids": list(MANDATORY_CASES),
    }
    kwargs.update(overrides)
    return REGRESSION.validate_regression_payload(payload, **kwargs)


def test_f8_complete_regression_payload_passes():
    result = _validate_regression(_regression_payload())
    assert result["status"] == "PASS", result
    assert all(result["checks"].values()), result


def test_f8_missing_comparison_snapshot_is_not_proven():
    result = _validate_regression(_regression_payload(comparison={}))
    assert result["status"] == "NOT_PROVEN", result
    assert any("Comparison Snapshot" in reason for reason in result["reasons"])


def test_f8_scope_five_cases_but_only_four_results_cannot_pass():
    result = _validate_regression(_regression_payload(mandatory_case_results=_case_results(4)))
    assert result["status"] != "PASS", result
    assert MANDATORY_CASES[4] in result["details"].get("returned_case_ids", []) or any(
        MANDATORY_CASES[4] in reason for reason in result["reasons"]
    )


def test_f8_fixed_sha_mismatch_is_not_proven():
    payload = _regression_payload()
    payload["regression"]["fixed_sha"] = OTHER_SHA
    result = _validate_regression(payload)
    assert result["status"] != "PASS", result
    assert result["checks"]["fixed_sha_matches"] is False


def test_f8_invalid_fixed_sha_is_rejected_before_any_call():
    errors = REGRESSION.validate_arguments(
        api_base="http://127.0.0.1:8000",
        defect_id=DEFECT_ID,
        fixed_commit_sha="abc1234",
        scope_snapshot=_scope(),
        idempotency_key="k-1",
    )
    assert any("40 位" in error for error in errors), errors
    assert REGRESSION.validate_arguments(
        api_base="http://127.0.0.1:8000",
        defect_id=DEFECT_ID,
        fixed_commit_sha=SHA,
        scope_snapshot=_scope(),
        idempotency_key="k-1",
    ) == []


def test_f8_other_defect_response_cannot_be_used():
    payload = _regression_payload()
    payload["regression"]["defect_id"] = DEFECT_ID + 1
    result = _validate_regression(payload)
    assert result["status"] == "NOT_PROVEN", result
    assert any("不一致" in reason for reason in result["reasons"])


def test_f8_failed_mandatory_case_stays_fail():
    payload = _regression_payload()
    payload["mandatory_case_results"][0]["status"] = "FAIL"
    payload["regression"]["status"] = "FAIL"
    result = _validate_regression(payload)
    assert result["status"] == "FAIL", result


def test_f8_original_defect_keeps_open_after_failed_regression():
    state = REGRESSION.resolve_defect_state(
        defect_id="WWY-V5-001",
        current_state="OPEN",
        regression_status="FAIL",
        regression_defect_id="WWY-V5-001",
        passing_case_ids=("WWY-V5-006",),
    )
    assert state["state"] == "OPEN"
    assert state["changed"] is False
    assert any("WWY-V5-006" in reason for reason in state["reasons"])


def test_f8_other_case_pass_does_not_close_original_defect():
    state = REGRESSION.resolve_defect_state(
        defect_id="WWY-V5-001",
        current_state="OPEN",
        regression_status="PASS",
        regression_defect_id="WWY-V5-006",
        passing_case_ids=("WWY-V5-006",),
    )
    assert state["state"] == "OPEN"
    assert state["changed"] is False


def test_f8_own_regression_pass_can_mark_fix_verified():
    state = REGRESSION.resolve_defect_state(
        defect_id="WWY-V5-001",
        current_state="OPEN",
        regression_status="PASS",
        regression_defect_id="WWY-V5-001",
    )
    assert state["state"] == "FIX_VERIFIED"
    assert state["changed"] is True


def _write_scope(tmp_path: Path) -> Path:
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(_scope(), ensure_ascii=False), encoding="utf-8")
    return path


def _closed_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def test_f8_unreachable_api_is_blocked_not_pass(tmp_path):
    output = tmp_path / "regression.json"
    result = _run_script(
        REGRESSION_SCRIPT,
        [
            "--api-base",
            f"http://127.0.0.1:{_closed_port()}",
            "--project-id",
            "1",
            "--defect-id",
            str(DEFECT_ID),
            "--fixed-commit-sha",
            SHA,
            "--scope-snapshot",
            str(_write_scope(tmp_path)),
            "--idempotency-key",
            "wwy-v5-001-run-1",
            "--token-env",
            "AIQE_API_TOKEN",
            "--timeout",
            "2",
            "--wait-seconds",
            "1",
            "--output",
            str(output),
        ],
        env={"AIQE_API_TOKEN": "fixture-api-token"},
    )
    assert result.returncode != 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED", payload
    assert payload["defect_state"]["state"] == "OPEN"


def test_f8_missing_arguments_are_blocked(tmp_path):
    output = tmp_path / "blocked.json"
    result = _run_script(REGRESSION_SCRIPT, ["--output", str(output)])
    assert result.returncode != 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED", payload
    assert any("--fixed-commit-sha" in reason for reason in payload["reasons"])


def test_f8_missing_secret_token_is_blocked(tmp_path):
    output = tmp_path / "blocked-token.json"
    result = _run_script(
        REGRESSION_SCRIPT,
        [
            "--api-base",
            "http://127.0.0.1:1",
            "--defect-id",
            str(DEFECT_ID),
            "--fixed-commit-sha",
            SHA,
            "--scope-snapshot",
            str(_write_scope(tmp_path)),
            "--idempotency-key",
            "wwy-v5-001-run-2",
            "--output",
            str(output),
        ],
        env={"AIQE_API_TOKEN": ""},
    )
    assert result.returncode != 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED"
    assert any("AIQE_API_TOKEN" in reason for reason in payload["reasons"])


def test_f8_remember_account_is_single_case_and_requires_formal_regression():
    observation = {
        "executed": True,
        "checks": {
            "username_refilled": True,
            "remember_me_true": True,
            "stored_username_matches": True,
        },
    }
    without_regression = REMEMBER.evaluate_single_case(observation, {})
    assert without_regression["status"] == "NOT_PROVEN", without_regression
    assert without_regression["missing_regression_evidence"]
    failed = REMEMBER.evaluate_single_case(
        {**observation, "checks": {"username_refilled": False}}, {}
    )
    assert failed["status"] == "FAIL", failed
    blocked = REMEMBER.evaluate_single_case(
        {"blocked_reason": "缺少 Secret: FUTUREWAYU_TEST_USERNAME"}, {}
    )
    assert blocked["status"] == "BLOCKED", blocked


def test_f8_remember_account_without_secret_is_blocked(tmp_path):
    result = _run_script(REMEMBER_SCRIPT, ["--out-dir", str(tmp_path)])
    assert result.returncode != 0, result.stdout + result.stderr
    payload = json.loads((tmp_path / "remember-account.json").read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED", payload
    assert payload["defect_id"] == "WWY-V5-006"
    assert payload["case_id"] == "TC-ADM-01-D"
    assert payload["product_tc_status"] == "NOT_PROVEN"
    assert payload["defect_state_unchanged"] == ["WWY-V5-001"]


# ────────────────────────── FIX-010：生产阶段 ──────────────────────────
def _stage(**overrides) -> dict:
    stage = {
        "status": "PASS",
        "target_release_sha": SHA,
        "deployed_image_digest": DIGEST,
        "environment": "production",
        "started_at": "2026-11-28T00:00:00Z",
        "finished_at": "2026-11-28T00:10:00Z",
        "checks": {"health": {"status": 200}},
        "artifact_refs": [CANARY],
        "operator_identity": "deploy-bot",
    }
    stage.update(overrides)
    return stage


def _production_payload(root: Path, **stage_overrides) -> dict:
    artifact = root / CANARY
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}\n", encoding="utf-8")
    stages = {key: _stage() for key in PRODUCTION.MANDATORY_STAGES}
    stages["rollback_drill"] = _stage(
        rollback_target_sha=OTHER_SHA,
        verification={"health": 200, "business_assertion": "PASS"},
        recovery_seconds=120,
    )
    stages["stage5_ga"] = _stage()
    stages.update(stage_overrides)
    return {
        "stages": stages,
        "independent_verification": {
            "reviewed_by": "MoojinR",
            "review_id": "PRR-1",
            "reviewed_commit_sha": SHA,
        },
    }


def _validate_production(root: Path, payload: dict, **kwargs):
    return PRODUCTION.validate_production_evidence(
        payload, expected_commit=SHA, root=root, **kwargs
    )


def test_f10_complete_production_fixture_passes(tmp_path):
    check = _validate_production(tmp_path, _production_payload(tmp_path))
    assert check.status == "PASS", check.as_dict()


def test_f10_skipped_stage_written_as_pass_is_rejected(tmp_path):
    skipped = _validate_production(
        tmp_path,
        _production_payload(
            tmp_path,
            stage3_small_traffic=_stage(status="SKIPPED", checks={"stage_executed": False}),
        ),
    )
    assert skipped.status != "PASS", skipped.as_dict()

    no_observation = _validate_production(
        tmp_path,
        _production_payload(
            tmp_path,
            stage3_small_traffic=_stage(
                checks={"planned_traffic_percent": 5, "observed_traffic_percent": None}
            ),
        ),
    )
    assert no_observation.status != "PASS", no_observation.as_dict()


def test_f10_waived_without_approver_or_expiry_is_rejected(tmp_path):
    incomplete = _validate_production(
        tmp_path,
        _production_payload(
            tmp_path,
            stage3_small_traffic=_stage(
                status="WAIVED",
                approved_by="",
                approved_at="2026-11-27T00:00:00Z",
                reason="跳过 5%",
                risk="未知",
                compensating_controls="100% 直切 + 回滚命令",
                expires_at="",
            ),
        ),
    )
    assert incomplete.status != "PASS", incomplete.as_dict()
    assert any("approved_by" in reason for reason in incomplete.reasons)
    assert any("expires_at" in reason for reason in incomplete.reasons)


def test_f10_expired_waiver_is_rejected_and_never_passes(tmp_path):
    expired = _validate_production(
        tmp_path,
        _production_payload(
            tmp_path,
            stage3_small_traffic=_stage(
                status="WAIVED",
                approved_by="release-owner",
                approved_at="2026-11-27T00:00:00Z",
                reason="用户授权 100% 直切",
                risk="跳过 5%/50% 观察",
                compensating_controls="回滚命令 + 监控",
                expires_at="2026-12-01T00:00:00Z",
            ),
        ),
        allow_waivers=True,
        now=datetime(2027, 1, 1, tzinfo=UTC),
    )
    assert expired.status != "PASS", expired.as_dict()
    assert any("已过期" in reason for reason in expired.reasons)


def test_f10_complete_waiver_still_never_passes(tmp_path):
    waived = _validate_production(
        tmp_path,
        _production_payload(
            tmp_path,
            stage3_small_traffic=_stage(
                status="WAIVED",
                approved_by="release-owner",
                approved_at="2026-11-27T00:00:00Z",
                reason="用户授权 100% 直切",
                risk="跳过 5% 观察",
                compensating_controls="回滚命令 + 监控",
                expires_at="2027-06-30T00:00:00Z",
            ),
        ),
        allow_waivers=True,
        now=datetime(2026, 12, 1, tzinfo=UTC),
    )
    assert waived.status != "PASS", waived.as_dict()
    assert any("WAIVED" in reason for reason in waived.reasons)


def test_f10_rollback_command_only_is_not_a_drill(tmp_path):
    command_only = _validate_production(
        tmp_path,
        _production_payload(
            tmp_path,
            rollback_drill=_stage(
                rollback_command="docker cp backup.conf frontend && nginx -s reload",
                nginx_backup="/root/nginx-default-before-canary.conf",
                verification={},
                recovery_seconds=None,
            ),
        ),
    )
    assert command_only.status != "PASS", command_only.as_dict()
    reasons = " ".join(command_only.reasons)
    assert "rollback_target_sha" in reasons
    assert "回滚后验证" in reasons


def test_f10_repo_production_evidence_is_not_pass():
    payload = json.loads(PRODUCTION_EVIDENCE.read_text(encoding="utf-8"))
    stages = payload["stages"]
    assert stages["stage1_shadow"]["status"] == "NOT_PROVEN"
    assert stages["stage2_dogfood"]["status"] == "NOT_PROVEN"
    assert stages["stage3_small_traffic"]["status"] == "NOT_RUN"
    assert stages["stage4_expand"]["status"] == "NOT_RUN"
    assert stages["stage5_ga"]["status"] in {"NOT_RUN", "NOT_PROVEN"}
    assert stages["rollback_drill"]["status"] == "NOT_RUN"
    assert stages["rollback_drill"]["blocked_by"]
    assert stages["rollback_drill"]["owner"]
    assert stages["rollback_drill"]["unblock_action"]
    verification = payload["independent_verification"]
    assert verification["reviewed_by"] == "MoojinR"
    assert verification["review_id"] == ""
    assert verification["reviewed_commit_sha"] == ""
    assert verification["status"] == "PENDING"

    check = PRODUCTION.validate_production_evidence(payload, root=REPO_ROOT)
    assert check.status in {"FAIL", "NOT_PROVEN", "BLOCKED", "NOT_RUN"}, check.as_dict()


def test_f10_repo_gate_f_is_not_pass():
    check, _artifacts = RELEASE_VERDICT.evaluate_gate_f(root=REPO_ROOT)
    assert check.status != "PASS", check.as_dict()
    assert any("rollback_drill" in reason for reason in check.reasons)


def test_f10_require_ga_cli_exits_nonzero_for_gate_f():
    result = _run_script(RELEASE_VERDICT_SCRIPT, ["--require-ga"])
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Gate F" in (result.stdout or "")
