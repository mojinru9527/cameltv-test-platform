"""V16-025 Gate G / FIX-013：Branch Protection / Ruleset 精确校验。

旧行为是“required checks 非空即通过”，无法阻止 AIQE Gate 被移除。
FIX-013 后必须精确校验 4 个 context（含 AIQE 聚合 Gate），并校验来源 App。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/check_branch_protection.py"
EVIDENCE = REPO_ROOT / "docs/aiqe/v1.6/governance/branch-protection.json"

REQUIRED_CHECKS = [
    "后端全新检出与全量回归",
    "前端全新检出与全量回归",
    "AI/Git 交付策略",
    "AIQE V1.6 Governance Gate",
]
BASE_CHECKS = REQUIRED_CHECKS[:3]
AIQE_CHECK = REQUIRED_CHECKS[3]
GITHUB_ACTIONS_APP_ID = 15368


def _load():
    spec = importlib.util.spec_from_file_location("branch_protection", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def _ruleset(integration_ids: dict[str, int] | None = None) -> list[dict]:
    ids = integration_ids or {name: GITHUB_ACTIONS_APP_ID for name in REQUIRED_CHECKS}
    return [
        {
            "id": 18351498,
            "name": "protect-main",
            "enforcement": "active",
            "target": "branch",
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
                        "strict_required_status_checks_policy": True,
                        "required_status_checks": [
                            {"context": context, "integration_id": app_id}
                            for context, app_id in ids.items()
                        ],
                    },
                },
            ],
        }
    ]


def _payload(**overrides):
    payload = {
        "verified": True,
        "source": "github-api",
        "required_checks": list(REQUIRED_CHECKS),
        "require_pr_before_merge": True,
        "require_non_author_review": True,
        "allow_force_push": False,
        "allow_deletions": False,
        "checked_at": "2026-11-28T00:00:00+00:00",
        "ruleset_ids": [18351498],
        "rulesets": _ruleset(),
    }
    payload.update(overrides)
    return payload


def test_complete_evidence_passes():
    assert MODULE.validate(_payload()) == []


def test_unverified_evidence_fails():
    errors = MODULE.validate({"verified": False, "reason": "无导出"})
    assert any("未验证" in item for item in errors)


def test_missing_aiqe_aggregate_check_fails():
    """少一个 AIQE 聚合 Gate（其他三个都在）必须失败，不能“非空即通过”。"""
    errors = MODULE.validate(
        _payload(required_checks=list(BASE_CHECKS), rulesets=_ruleset({c: 15368 for c in BASE_CHECKS}))
    )
    assert any(AIQE_CHECK in item for item in errors), errors


def test_renamed_aiqe_check_fails():
    renamed = BASE_CHECKS + ["AIQE V1.6 治理门禁"]
    errors = MODULE.validate(
        _payload(required_checks=renamed, rulesets=_ruleset({c: 15368 for c in renamed}))
    )
    assert any(AIQE_CHECK in item for item in errors), errors


def test_extra_unrelated_check_passes():
    extra = REQUIRED_CHECKS + ["某个额外观察检查"]
    errors = MODULE.validate(
        _payload(required_checks=extra, rulesets=_ruleset({c: 15368 for c in extra}))
    )
    assert errors == []


def test_aiqe_check_from_untrusted_app_fails():
    """同名但 integration_id 不是 GitHub Actions(15368) 的 check 不能冒充。"""
    ids = {name: GITHUB_ACTIONS_APP_ID for name in BASE_CHECKS}
    ids[AIQE_CHECK] = 999999
    errors = MODULE.validate(_payload(required_checks=list(REQUIRED_CHECKS), rulesets=_ruleset(ids)))
    assert any("不可信" in item and "999999" in item for item in errors), errors


def test_legacy_two_check_payload_fails():
    """旧规则下的两 check 证据（无 AIQE、无 checked_at/ruleset id）必须失败。"""
    legacy = {
        "verified": True,
        "required_checks": ["后端全新检出与全量回归", "前端全新检出与全量回归"],
        "require_pr_before_merge": True,
        "require_non_author_review": True,
        "allow_force_push": False,
        "allow_deletions": False,
        "rulesets": _ruleset(
            {
                "后端全新检出与全量回归": 15368,
                "前端全新检出与全量回归": 15368,
            }
        ),
    }
    errors = MODULE.validate(legacy)
    assert errors
    assert any(AIQE_CHECK in item for item in errors), errors
    assert any("checked_at" in item for item in errors), errors
    assert any("ruleset id" in item for item in errors), errors


def test_missing_checked_at_fails():
    errors = MODULE.validate(_payload(checked_at=""))
    assert any("checked_at" in item for item in errors), errors


def test_missing_ruleset_id_fails():
    errors = MODULE.validate(_payload(ruleset_ids=[]))
    assert any("ruleset id" in item for item in errors), errors


def test_non_author_review_required():
    errors = MODULE.validate(_payload(require_non_author_review=False))
    assert any("非作者审批" in item for item in errors)


def test_force_push_and_deletion_must_be_disabled():
    errors = MODULE.validate(_payload(allow_force_push=True, allow_deletions=True))
    assert any("强推" in item for item in errors)
    assert any("删除" in item for item in errors)


def test_check_sources_untrusted_app_fails():
    sources = {context: {"app_id": GITHUB_ACTIONS_APP_ID} for context in REQUIRED_CHECKS}
    sources[AIQE_CHECK] = {"app_id": 123456}
    errors = MODULE.validate(_payload(check_sources=sources))
    assert any("不可信" in item and AIQE_CHECK in item for item in errors), errors


def test_check_sources_trusted_app_passes():
    sources = {context: {"app_id": GITHUB_ACTIONS_APP_ID} for context in REQUIRED_CHECKS}
    assert MODULE.validate(_payload(check_sources=sources)) == []


def test_repo_evidence_is_real_and_consistent():
    """仓库内证据必须来自 GitHub API，且字段与 rulesets 明细一致。"""
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if payload.get("verified"):
        assert payload["source"] == "github-api"
        assert payload["ruleset_ids"], "verified 证据必须包含 ruleset id"
        assert payload.get("checked_at"), "verified 证据必须包含采集时间"
        rules = [
            rule.get("type")
            for ruleset in payload.get("rulesets") or []
            for rule in ruleset.get("rules") or []
        ]
        if "non_fast_forward" in rules:
            assert payload["allow_force_push"] is False
        if "deletion" in rules:
            assert payload["allow_deletions"] is False
        if "required_status_checks" in rules:
            assert payload["required_checks"], "ruleset 声明 required_status_checks 时必须有 context"


def test_cli_check_accepts_valid_evidence(tmp_path):
    target = tmp_path / "branch-protection.json"
    target.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    assert MODULE.main(["--check", "--target", str(target)]) == 0


def test_cli_check_rejects_missing_aiqe_check(tmp_path):
    target = tmp_path / "branch-protection.json"
    payload = _payload(
        required_checks=list(BASE_CHECKS), rulesets=_ruleset({c: 15368 for c in BASE_CHECKS})
    )
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert MODULE.main(["--check", "--target", str(target)]) == 1
