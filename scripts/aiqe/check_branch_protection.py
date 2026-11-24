"""V16-025 Gate G：Branch Protection / Ruleset 证据采集与校验。

Gate G 要求“禁止直接 push main、必需 CI、非作者审批”有**外部系统证据**，
不能只用 CODEOWNERS 或文档声明代替。本脚本提供两条路径：

``--capture``
    用 GitHub API 查询仓库 ruleset / branch protection，写入
    ``docs/aiqe/v1.6/governance/branch-protection.json``。需要 ``GITHUB_TOKEN``
    与网络；失败时非零退出且不掩盖原因。

``--check``
    校验已提交的 JSON：``verified=true`` 时必须有 required_checks、
    require_pr_before_merge、require_non_author_review、allow_force_push=false、
    allow_deletions=false；``verified=false`` 时直接非零退出（Gate G 未完成）。

令牌只从环境变量读取，不落盘、不打印。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "docs/aiqe/v1.6/governance/branch-protection.json"
API = "https://api.github.com"


class CaptureError(RuntimeError):
    pass


def _request(path: str, token: str) -> tuple[int, object]:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cameltv-aiqe-governance",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return exc.code, {"error": body[:500]}
    except (urllib.error.URLError, TimeoutError) as exc:
        raise CaptureError(f"无法连接 GitHub API: {exc}") from exc


def capture(repo: str, branch: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise CaptureError("缺少 GITHUB_TOKEN/GH_TOKEN，无法采集 Branch Protection 证据")
    protection_status, protection = _request(f"/repos/{repo}/branches/{branch}/protection", token)
    rulesets_status, rulesets = _request(f"/repos/{repo}/rulesets?targets=branch", token)
    if protection_status == 404:
        protection = {}
    elif protection_status != 200:
        raise CaptureError(f"查询 branch protection 失败: HTTP {protection_status} {protection}")
    if rulesets_status != 200:
        raise CaptureError(f"查询 rulesets 失败: HTTP {rulesets_status} {rulesets}")

    required_checks: list[str] = []
    checks = ((protection or {}).get("required_status_checks") or {}).get("contexts") or []
    required_checks.extend(str(item) for item in checks)
    reviews = (protection or {}).get("required_pull_request_reviews") or {}
    ruleset_summary = []
    for item in rulesets or []:
        if not isinstance(item, dict):
            continue
        ruleset_summary.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "enforcement": item.get("enforcement"),
                "target": item.get("target"),
                "conditions": item.get("conditions"),
            }
        )
    verified = bool(protection or ruleset_summary)
    return {
        "schema_version": "1.0",
        "repository": repo,
        "branch": branch,
        "verified": verified,
        "checked_at": datetime.now(UTC).isoformat(),
        "source": "github-api",
        "reason": "" if verified else "GitHub 未返回 branch protection 或 ruleset 配置",
        "required_checks": sorted(set(required_checks)),
        "require_pr_before_merge": bool(reviews) or None,
        "require_non_author_review": bool(reviews.get("require_code_owner_reviews"))
        if reviews
        else None,
        "allow_force_push": ((protection or {}).get("allow_force_pushes") or {}).get("enabled"),
        "allow_deletions": ((protection or {}).get("allow_deletions") or {}).get("enabled"),
        "ruleset_ids": [item.get("id") for item in ruleset_summary if item.get("id")],
        "rulesets": ruleset_summary,
        "capture_command": (
            f"python scripts/aiqe/check_branch_protection.py --capture --repo {repo} --branch {branch}"
        ),
    }


def validate(payload: dict) -> list[str]:
    errors: list[str] = []
    if not payload.get("verified"):
        errors.append(
            "Branch Protection 未验证：" + str(payload.get("reason") or "缺少 GitHub API 证据")
        )
        return errors
    if not payload.get("required_checks"):
        errors.append("缺少 required_status_checks（Gate G 要求必需 CI）")
    if payload.get("require_pr_before_merge") is not True:
        errors.append("未证明必须通过 PR 合入（require_pull_request_reviews）")
    if payload.get("allow_force_push") is not False:
        errors.append("未证明禁止强推（allow_force_pushes 必须为 false）")
    if payload.get("allow_deletions") is not False:
        errors.append("未证明禁止删除分支（allow_deletions 必须为 false）")
    if payload.get("require_non_author_review") is not True:
        errors.append("未证明 CODEOWNERS / 非作者审批生效")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIQE Gate G Branch Protection 证据")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repo", default="mojinru9527/cameltv-test-platform")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--target", default=str(TARGET))
    args = parser.parse_args(argv)

    target = Path(args.target)
    if args.capture:
        try:
            payload = capture(args.repo, args.branch)
        except CaptureError as exc:
            print(f"::error::[branch-protection] {exc}")
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"written {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
        errors = validate(payload)
        for error in errors:
            print(f"::error::[branch-protection] {error}")
        return 0 if not errors else 1

    if not target.exists():
        print(f"::error::[branch-protection] 证据文件不存在: {target}")
        return 1
    payload = json.loads(target.read_text(encoding="utf-8"))
    errors = validate(payload)
    for error in errors:
        print(f"::error::[branch-protection] {error}")
    if not errors:
        print(json.dumps({"ok": True, "repository": payload.get("repository")}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
