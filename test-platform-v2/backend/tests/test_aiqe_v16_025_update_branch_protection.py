"""V16-025 Gate G / FIX-013：ruleset 非作者审批 + AIQE required check 的离线单测。

全部函数级测试，不访问 GitHub API；真实 Ruleset 变更必须人工审批后执行。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/update_branch_protection.py"

REQUIRED_CHECKS = [
    "后端全新检出与全量回归",
    "前端全新检出与全量回归",
    "AI/Git 交付策略",
    "AIQE V1.6 Governance Gate",
]
AIQE_CHECK = REQUIRED_CHECKS[3]


def _load():
    spec = importlib.util.spec_from_file_location("update_branch_protection", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def _rules(contexts: list[str]) -> list[dict]:
    return [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "require_code_owner_review": True,
                "required_approving_review_count": 1,
                "allowed_merge_methods": ["squash"],
            },
        },
        {
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": True,
                "required_status_checks": [
                    {"context": context, "integration_id": 15368} for context in contexts
                ],
            },
        },
    ]


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


def test_ensure_appends_only_missing_aiqe_context():
    """已有 3 个 context 时只追加 AIQE 聚合 Gate，保留其他规则与已有 check 明细。"""
    rules = _rules(REQUIRED_CHECKS[:3])
    updated = MODULE.ensure_required_contexts(rules)
    contexts = MODULE.required_contexts(updated)
    assert contexts == REQUIRED_CHECKS
    # 已有规则与其他 check 明细保持不变
    assert {item["type"] for item in updated} >= {
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_status_checks",
    }
    pull = next(item for item in updated if item["type"] == "pull_request")
    assert pull["parameters"]["allowed_merge_methods"] == ["squash"]
    checks = next(item for item in updated if item["type"] == "required_status_checks")
    entries = checks["parameters"]["required_status_checks"]
    assert checks["parameters"]["strict_required_status_checks_policy"] is True
    assert {entry["context"] for entry in entries} == set(REQUIRED_CHECKS)
    assert all(entry["integration_id"] == 15368 for entry in entries)
    # 输入不被就地修改（幂等设计的前提）
    assert MODULE.required_contexts(rules) == REQUIRED_CHECKS[:3]


def test_ensure_is_idempotent():
    once = MODULE.ensure_required_contexts(_rules(REQUIRED_CHECKS[:3]))
    twice = MODULE.ensure_required_contexts(once)
    assert MODULE.required_contexts(twice) == REQUIRED_CHECKS
    assert once == twice


def test_ensure_preserves_existing_integration_ids():
    rules = _rules(REQUIRED_CHECKS[:3])
    checks = next(item for item in rules if item["type"] == "required_status_checks")
    checks["parameters"]["required_status_checks"][0]["integration_id"] = 424242
    updated = MODULE.ensure_required_contexts(rules)
    entries = next(
        item for item in updated if item["type"] == "required_status_checks"
    )["parameters"]["required_status_checks"]
    by_context = {entry["context"]: entry for entry in entries}
    assert by_context[REQUIRED_CHECKS[0]]["integration_id"] == 424242
    assert by_context[AIQE_CHECK]["integration_id"] == 15368


def test_ensure_adds_required_status_checks_rule_when_missing():
    updated = MODULE.ensure_required_contexts([{"type": "deletion"}])
    assert MODULE.required_contexts(updated) == REQUIRED_CHECKS
    checks = next(item for item in updated if item["type"] == "required_status_checks")
    assert checks["parameters"]["required_status_checks"][-1]["context"] == AIQE_CHECK


def test_context_change_summary_reports_before_after():
    before = _rules(REQUIRED_CHECKS[:3])
    after = MODULE.ensure_required_contexts(before)
    summary = MODULE.context_change_summary(before, after)
    assert summary["before"] == REQUIRED_CHECKS[:3]
    assert summary["after"] == REQUIRED_CHECKS
    assert summary["added"] == [AIQE_CHECK]
