"""V16-025 Gate G：为 `protect-main` ruleset 启用非作者审批（安全检查 + 可重放）。

背景
----
GitHub Ruleset `protect-main (#18351498)` 已启用 required checks/禁强推/禁删除/必须 PR，
但 `require_code_owner_review=false` 且 `required_approving_review_count=0`。
单人仓库直接启用会**永久锁死合并**（作者不能自批、无 bypass）。因此本脚本：

1. 读取仓库 collaborators 与 ruleset 明细；
2. 若没有 `--apply` → 只打印将要修改的字段（dry-run）；
3. 若有 `--apply`：
   - 要求至少 2 个协作者，且 `--reviewer-login` 是其中之一（否则拒绝）；
   - 用 GitHub API 更新 ruleset：`require_code_owner_review=true`、
     `required_approving_review_count>=1`（参数默认 1）；
   - 重新采集 `governance/branch-protection.json` 供 Gate G 判定。

用法
----
    # 干跑（安全）：看看当前还缺什么
    python scripts/aiqe/update_branch_protection.py --reviewer-login <独立账号>

    # 真改（需要该账号已是 collaborator、且仓库管理员 token）
    python scripts/aiqe/update_branch_protection.py --reviewer-login <独立账号> --apply

    # 改完后重算
    python scripts/aiqe/check_branch_protection.py --capture
    python scripts/aiqe/release_verdict.py --write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = "mojinru9527/cameltv-test-platform"
RULESET_ID = 18351498


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
    parser = argparse.ArgumentParser(description="启用 ruleset 非作者审批（安全版）")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--ruleset-id", type=int, default=RULESET_ID)
    parser.add_argument("--reviewer-login", required=True)
    parser.add_argument("--approvals", type=int, default=1)
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
    rules = patch_pull_request_rule(list(ruleset.get("rules") or []), approvals=args.approvals)
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
        "changes": {
            "require_code_owner_review": True,
            "required_approving_review_count": args.approvals,
        },
        "dry_run": not args.apply,
    }
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
