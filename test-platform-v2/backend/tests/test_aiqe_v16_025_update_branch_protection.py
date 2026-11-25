"""V16-025 Gate G：ruleset 非作者审批更新的安全检查（离线单测）。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/update_branch_protection.py"


def _load():
    spec = importlib.util.spec_from_file_location("update_branch_protection", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_single_account_repo_refuses_to_enable_review():
    with pytest.raises(MODULE.UpdateError) as excinfo:
        MODULE.ensure_independent_reviewer(["mojinru9527"], "mojinru9527")
    assert "永久锁死" in str(excinfo.value)


def test_reviewer_must_be_collaborator():
    with pytest.raises(MODULE.UpdateError) as excinfo:
        MODULE.ensure_independent_reviewer(["mojinru9527", "qa-reviewer"], "other-user")
    assert "不是仓库协作者" in str(excinfo.value)


def test_two_collaborators_pass():
    MODULE.ensure_independent_reviewer(["mojinru9527", "qa-reviewer"], "qa-reviewer")


def test_patch_pull_request_rule_sets_non_author_review():
    rules = [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "require_code_owner_review": False,
                "required_approving_review_count": 0,
                "allowed_merge_methods": ["squash"],
            },
        },
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": "后端全新检出与全量回归"}]},
        },
    ]
    updated = MODULE.patch_pull_request_rule(rules, approvals=1)
    pull = next(item for item in updated if item["type"] == "pull_request")
    assert pull["parameters"]["require_code_owner_review"] is True
    assert pull["parameters"]["required_approving_review_count"] == 1
    # 其他规则不得被破坏
    assert {item["type"] for item in updated} >= {
        "deletion",
        "non_fast_forward",
        "required_status_checks",
    }
    assert pull["parameters"]["allowed_merge_methods"] == ["squash"]


def test_patch_adds_pull_request_rule_when_missing():
    updated = MODULE.patch_pull_request_rule([{"type": "deletion"}], approvals=2)
    pull = next(item for item in updated if item["type"] == "pull_request")
    assert pull["parameters"]["require_code_owner_review"] is True
    assert pull["parameters"]["required_approving_review_count"] == 2
