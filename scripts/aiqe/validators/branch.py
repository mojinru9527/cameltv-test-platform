"""Main Ruleset / Branch Protection 精确校验（FIX-013）。

要求 required checks 精确包含 AIQE 聚合 Gate，而不是“非空即可”。
同名但来源不可信的 check 也不能算数。
"""
from __future__ import annotations

from typing import Any

from validators.models import GateCheck

BASE_REQUIRED_CHECKS = (
    "后端全新检出与全量回归",
    "前端全新检出与全量回归",
    "AI/Git 交付策略",
)
AIQE_AGGREGATE_CHECK = "AIQE V1.6 Governance Gate"
REQUIRED_CHECKS = BASE_REQUIRED_CHECKS + (AIQE_AGGREGATE_CHECK,)
TRUSTED_APPS = {15368}  # github-actions[bot]


def _check_names(payload: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for raw in payload.get("required_checks") or []:
        names.add(str(raw))
    for ruleset in payload.get("rulesets") or []:
        for rule in ruleset.get("rules") or []:
            if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                continue
            for item in (rule.get("parameters") or {}).get("required_status_checks") or []:
                context = str((item or {}).get("context") or "").strip()
                if context:
                    names.add(context)
    return names


def validate_branch_protection(
    payload: Any,
    *,
    required: tuple[str, ...] = REQUIRED_CHECKS,
    require_aiqe: bool = True,
) -> GateCheck:
    check = GateCheck()
    if not isinstance(payload, dict):
        return GateCheck.unproven("缺少 branch-protection.json")
    if not payload.get("verified"):
        return GateCheck.unproven(
            "Branch Protection 未验证：" + str(payload.get("reason") or "缺少 GitHub API 证据")
        )
    names = _check_names(payload)
    missing = [item for item in required if item not in names]
    if require_aiqe and AIQE_AGGREGATE_CHECK not in names:
        check.add(f"Main Ruleset 未要求 AIQE 聚合 Gate: {AIQE_AGGREGATE_CHECK!r}")
    if missing:
        check.add(f"Main Ruleset 缺少 required checks: {missing}")
    if payload.get("require_pr_before_merge") is not True:
        check.add("未证明必须通过 PR 合入")
    if payload.get("allow_force_push") is not False:
        check.add("未证明禁止强推")
    if payload.get("allow_deletions") is not False:
        check.add("未证明禁止删除分支")
    if payload.get("require_non_author_review") is not True:
        check.add("未证明非作者审批生效")
    if not str(payload.get("checked_at") or "").strip():
        check.add("Ruleset 证据缺少 checked_at")
    if not payload.get("ruleset_ids"):
        check.add("Ruleset 证据缺少 ruleset id")

    # 若证据包含 check source/app id，则必须来自可信 GitHub App。
    for ruleset in payload.get("rulesets") or []:
        for rule in ruleset.get("rules") or []:
            if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                continue
            for item in (rule.get("parameters") or {}).get("required_status_checks") or []:
                if not isinstance(item, dict):
                    continue
                app_id = item.get("integration_id") or item.get("app_id")
                context = str(item.get("context") or "")
                if app_id is not None and context == AIQE_AGGREGATE_CHECK and int(app_id) not in TRUSTED_APPS:
                    check.add(f"AIQE Gate 来源 App {app_id} 不可信")

    if check.reasons:
        return check
    check.status = "PASS"
    check.note(f"Main Ruleset 精确包含 {len(required)} 个 required checks（含 AIQE 聚合 Gate）")
    check.evidence_refs.append("docs/aiqe/v1.6/governance/branch-protection.json")
    return check


__all__ = [
    "AIQE_AGGREGATE_CHECK",
    "BASE_REQUIRED_CHECKS",
    "REQUIRED_CHECKS",
    "validate_branch_protection",
]
