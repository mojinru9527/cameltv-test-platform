"""V16-025 Gate G：Branch Protection / Ruleset 证据校验（check_branch_protection.py）。"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/check_branch_protection.py"
EVIDENCE = REPO_ROOT / "docs/aiqe/v1.6/governance/branch-protection.json"


def _load():
    spec = importlib.util.spec_from_file_location("branch_protection", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def _payload(**overrides):
    payload = {
        "verified": True,
        "required_checks": ["后代检查", "前端检查"],
        "require_pr_before_merge": True,
        "require_non_author_review": True,
        "allow_force_push": False,
        "allow_deletions": False,
    }
    payload.update(overrides)
    return payload


def test_complete_evidence_passes():
    assert MODULE.validate(_payload()) == []


def test_unverified_evidence_fails():
    errors = MODULE.validate({"verified": False, "reason": "无导出"})
    assert any("未验证" in item for item in errors)


def test_missing_checks_fails():
    errors = MODULE.validate(_payload(required_checks=[]))
    assert any("required_status_checks" in item for item in errors)


def test_non_author_review_required():
    errors = MODULE.validate(_payload(require_non_author_review=False))
    assert any("非作者审批" in item for item in errors)


def test_force_push_and_deletion_must_be_disabled():
    errors = MODULE.validate(_payload(allow_force_push=True, allow_deletions=True))
    assert any("强推" in item for item in errors)
    assert any("删除" in item for item in errors)


def test_repo_evidence_is_real_and_consistent():
    """仓库内证据必须来自 GitHub API，且字段与 rulesets 明细一致。"""
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if payload.get("verified"):
        assert payload["source"] == "github-api"
        assert payload["ruleset_ids"], "verified 证据必须包含 ruleset id"
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
