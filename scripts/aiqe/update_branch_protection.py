"""V16-025 Gate G / FIX-013：`protect-main` ruleset 的可重放治理更新。

本脚本在人工审批下执行两件事（默认 dry-run，只有 `--apply` 才写 GitHub）：

1. **纳入 AIQE 聚合 Gate（FIX-013）**：``--ensure-required-checks`` 读取现有 ruleset，
   幂等追加 4 个必需 context（后端/前端/AI-Git 交付策略/AIQE V1.6 Governance Gate）；
   只补缺失项，保留其他规则、已有 check 明细与 ``integration_id``。打印 before/after。
2. **启用非作者审批**：``require_code_owner_review=true`` 且
   ``required_approving_review_count>=1``。单人仓库直接启用会永久锁死合并
   （作者不能自批、无 bypass），因此要求至少 2 个协作者且 `--reviewer-login`
   是其中之一，否则拒绝。

更新后需重新采集证据并重算判定：
``python scripts/aiqe/check_branch_protection.py --capture`` +
``python scripts/aiqe/release_verdict.py --write``。

用法
----
    # 干跑（安全）：看看 required checks 与审批字段还缺什么
    python scripts/aiqe/update_branch_protection.py --reviewer-login <独立账号> \
        --ensure-required-checks

    # 真改（需要该账号已是 collaborator、且仓库管理员 token / 人工审批）
    python scripts/aiqe/update_branch_protection.py --reviewer-login <独立账号> \
        --ensure-required-checks --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover - 直接执行时
    sys.path.insert(0, str(SCRIPT_DIR))

from validators.branch import REQUIRED_CHECKS  # noqa: E402

API = "https://api.github.com"
REPO = "mojinru9527/cameltv-test-platform"
RULESET_ID = 18351498
# GitHub Actions App id；只用于补齐缺失 context，不覆盖已有 check 的 integration_id。
ACTIONS_INTEGRATION_ID = 15368


class UpdateError(RuntimeError):
    pass


def _request(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, object]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cameltv-aiqe-governance",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return exc.code, {"error": body[:500]}


def ensure_independent_reviewer(collaborators: list[str], reviewer: str) -> None:
    """单账号仓库不允许直接启用非作者审批（会永久锁死合并）。"""
    normalized = {item.lower() for item in collaborators if item}
    if len(normalized) < 2:
        raise UpdateError(
            "仓库只有 1 个协作者，启用非作者审批会永久锁死合并；"
            "请先邀请独立 reviewer 账号再接 --apply"
        )
    if reviewer.lower() not in normalized:
        raise UpdateError(f"reviewer {reviewer!r} 不是仓库协作者（当前: {sorted(normalized)}）")


def required_contexts(rules: list[dict]) -> list[str]:
    """返回 ruleset 中所有 required_status_checks 的 context（保持声明顺序）。"""
    names: list[str] = []
    for rule in rules:
        if not isinstance(rule, dict) or str(rule.get("type")) != "required_status_checks":
            continue
        for item in (rule.get("parameters") or {}).get("required_status_checks") or []:
            context = str((item or {}).get("context") or "").strip()
            if context and context not in names:
                names.append(context)
    return names


def ensure_required_contexts(
    rules: list[dict],
    contexts: tuple[str, ...] = REQUIRED_CHECKS,
    *,
    integration_id: int | None = ACTIONS_INTEGRATION_ID,
) -> list[dict]:
    """幂等补齐 required check contexts，保留其他规则与已有 check 明细。

    只追加缺失的 context；已存在的 context（含其 integration_id/app_id）原样保留。
    没有 ``required_status_checks`` 规则时新建一条完整规则。
    """
    updated: list[dict] = []
    found = False
    for rule in rules:
        if not isinstance(rule, dict) or str(rule.get("type")) != "required_status_checks":
            updated.append(rule)
            continue
        found = True
        parameters = dict(rule.get("parameters") or {})
        raw_checks = parameters.get("required_status_checks") or []
        checks: list[dict] = [
            dict(item) if isinstance(item, dict) else {"context": str(item)} for item in raw_checks
        ]
        existing = {str(item.get("context") or "").strip() for item in checks}
        for context in contexts:
            name = str(context).strip()
            if not name or name in existing:
                continue
            entry: dict = {"context": name}
            if integration_id is not None:
                entry["integration_id"] = int(integration_id)
            checks.append(entry)
            existing.add(name)
        parameters["required_status_checks"] = checks
        updated.append({**rule, "parameters": parameters})
    if not found:
        checks = []
        for context in contexts:
            name = str(context).strip()
            if not name:
                continue
            entry = {"context": name}
            if integration_id is not None:
                entry["integration_id"] = int(integration_id)
            checks.append(entry)
        updated.append(
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "do_not_enforce_on_create": False,
                    "required_status_checks": checks,
                },
            }
        )
    return updated


def context_change_summary(before: list[dict], after: list[dict]) -> dict[str, list[str]]:
    before_names = required_contexts(before)
    after_names = required_contexts(after)
    return {
        "before": before_names,
        "after": after_names,
        "added": [name for name in after_names if name not in before_names],
    }


def patch_pull_request_rule(rules: list[dict], *, approvals: int = 1) -> list[dict]:
    updated: list[dict] = []
    found = False
    for rule in rules:
        if str(rule.get("type")) != "pull_request":
            updated.append(rule)
            continue
        found = True
        parameters = dict(rule.get("parameters") or {})
        parameters["require_code_owner_review"] = True
        parameters["required_approving_review_count"] = max(
            int(parameters.get("required_approving_review_count") or 0), approvals
        )
        updated.append({**rule, "parameters": parameters})
    if not found:
        updated.append(
            {
                "type": "pull_request",
                "parameters": {
                    "require_code_owner_review": True,
                    "required_approving_review_count": approvals,
                    "dismiss_stale_reviews_on_push": True,
                    "require_last_push_approval": False,
                    "required_review_thread_resolution": True,
                },
            }
        )
    return updated


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="AIQE ruleset 治理更新（required checks + 非作者审批）")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--ruleset-id", type=int, default=RULESET_ID)
    parser.add_argument("--reviewer-login", required=True)
    parser.add_argument("--approvals", type=int, default=1)
    parser.add_argument(
        "--ensure-required-checks",
        action="store_true",
        help="幂等补齐 4 个必需 context（含 AIQE V1.6 Governance Gate），保留其他规则",
    )
    parser.add_argument(
        "--integration-id",
        type=int,
        default=ACTIONS_INTEGRATION_ID,
        help="追加缺失 context 时写入的 GitHub App id（默认 GitHub Actions 15368）",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("::error::[branch-protection] 缺少 GITHUB_TOKEN/GH_TOKEN")
        return 2
    status, body = _request("GET", f"/repos/{args.repo}/collaborators", token)
    if status != 200 or not isinstance(body, list):
        print(f"::error::[branch-protection] 读取 collaborators 失败: HTTP {status} {body}")
        return 1
    collaborators = [str(item.get("login")) for item in body if isinstance(item, dict)]
    # 只把有 push/admin 权限的视为有效 reviewer（read 权限不能审批）
    status, perms = _request(
        "GET", f"/repos/{args.repo}/collaborators/{args.reviewer_login}/permission", token
    )
    if status != 200:
        print(f"::error::[branch-protection] 读取 reviewer 权限失败: HTTP {status} {perms}")
        return 1
    permission = str((perms or {}).get("permission") or "") if isinstance(perms, dict) else ""
    if permission not in {"push", "maintain", "admin", "write"}:
        print(
            f"::error::[branch-protection] reviewer {args.reviewer_login!r} 权限 {permission!r} "
            "不足以审批（需 push/maintain/admin）"
        )
        return 1
    try:
        ensure_independent_reviewer(collaborators, args.reviewer_login)
    except UpdateError as exc:
        print(f"::error::[branch-protection] {exc}")
        print(json.dumps({"ok": False, "collaborators": collaborators}, ensure_ascii=False))
        return 1

    status, ruleset = _request("GET", f"/repos/{args.repo}/rulesets/{args.ruleset_id}", token)
    if status != 200 or not isinstance(ruleset, dict):
        print(f"::error::[branch-protection] 读取 ruleset 失败: HTTP {status} {ruleset}")
        return 1
    existing_rules = list(ruleset.get("rules") or [])
    rules = existing_rules
    if args.ensure_required_checks:
        rules = ensure_required_contexts(
            rules, REQUIRED_CHECKS, integration_id=args.integration_id
        )
    checks_change = context_change_summary(existing_rules, rules)
    rules = patch_pull_request_rule(rules, approvals=args.approvals)
    payload = {
        "name": ruleset.get("name"),
        "target": ruleset.get("target", "branch"),
        "enforcement": ruleset.get("enforcement", "active"),
        "conditions": ruleset.get("conditions") or {},
        "rules": rules,
        "bypass_actors": ruleset.get("bypass_actors") or [],
    }
    plan = {
        "repository": args.repo,
        "ruleset_id": args.ruleset_id,
        "reviewer": args.reviewer_login,
        "ensure_required_checks": args.ensure_required_checks,
        "required_checks": checks_change,
        "changes": {
            "require_code_owner_review": True,
            "required_approving_review_count": args.approvals,
        },
        "dry_run": not args.apply,
    }
    print(f"required_checks before: {checks_change['before']}")
    print(f"required_checks after:  {checks_change['after']}")
    print(f"required_checks added:  {checks_change['added']}")
    if not args.apply:
        print(json.dumps({**plan, "ok": True, "note": "dry-run；加 --apply 才会修改"}, ensure_ascii=False))
        return 0
    status, result = _request(
        "PUT", f"/repos/{args.repo}/rulesets/{args.ruleset_id}", token, payload
    )
    if status not in {200, 201}:
        print(f"::error::[branch-protection] 更新 ruleset 失败: HTTP {status} {result}")
        return 1
    print(json.dumps({**plan, "ok": True, "updated": True}, ensure_ascii=False))
    print("下一步：python scripts/aiqe/check_branch_protection.py --capture && "
          "python scripts/aiqe/release_verdict.py --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
