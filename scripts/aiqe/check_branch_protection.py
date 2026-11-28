"""V16-025 Gate G / FIX-013：Branch Protection / Ruleset 证据采集与精确校验。

Gate G 要求“禁止直接 push main、必需 CI、非作者审批”有**外部系统证据**，
不能只用 CODEOWNERS 或文档声明代替。本脚本提供两条路径：

``--capture``
    用 GitHub API 查询仓库 ruleset / branch protection / 最近一次 check-runs，
    写入 ``docs/aiqe/v1.6/governance/branch-protection.json``。需要 ``GITHUB_TOKEN``
    与网络；失败时非零退出且不掩盖原因。证据包含：

    * ``required_checks``：required status check context 名单（精确名称）；
    * ``required_checks_detail``：每个 context 的 ruleset id/name 与
      ``integration_id``/``app_id``（来自 ruleset API；GitHub 未返回时为空）；
    * ``check_sources``：最近一次 commit 的 check-run 来源 App（id/slug/状态）；
    * ``ruleset_api_snapshot``：ruleset API 原始快照 + 采集时间 + 仓库/Ruleset ID。

``--check``
    调用 ``validators.branch.validate_branch_protection`` 精确校验 4 个 required
    contexts（后端全新检出与全量回归 / 前端全新检出与全量回归 / AI/Git 交付策略 /
    AIQE V1.6 Governance Gate）。缺任一、改名、来源 App 不可信、证据缺
    ``checked_at`` 或 ruleset id 均失败；**不再“非空即通过”**。

令牌只从环境变量读取，不落盘、不打印。本脚本只做只读查询，修改 Ruleset 由
``update_branch_protection.py`` 在人工审批下执行。
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
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover - 直接执行时
    sys.path.insert(0, str(SCRIPT_DIR))

from validators.branch import (  # noqa: E402
    AIQE_AGGREGATE_CHECK,
    REQUIRED_CHECKS,
    TRUSTED_APPS,
    validate_branch_protection,
)

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


def _required_check_names(
    protection: dict[str, Any] | None, rulesets: list[dict[str, Any]]
) -> list[str]:
    names: list[str] = []
    contexts = ((protection or {}).get("required_status_checks") or {}).get("contexts") or []
    for item in contexts:
        context = str(item or "").strip()
        if context:
            names.append(context)
    for ruleset in rulesets:
        for rule in ruleset.get("rules") or []:
            if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                continue
            for item in (rule.get("parameters") or {}).get("required_status_checks") or []:
                context = str((item or {}).get("context") or "").strip()
                if context:
                    names.append(context)
    return sorted(set(names))


def _required_check_details(rulesets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 ruleset 明细展开每个 required context 的来源（ruleset + integration/app id）。"""
    details: list[dict[str, Any]] = []
    for ruleset in rulesets:
        ruleset_id = ruleset.get("id")
        ruleset_name = ruleset.get("name")
        for rule in ruleset.get("rules") or []:
            if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                continue
            params = rule.get("parameters") or {}
            for item in params.get("required_status_checks") or []:
                if not isinstance(item, dict):
                    continue
                context = str(item.get("context") or "").strip()
                if not context:
                    continue
                details.append(
                    {
                        "context": context,
                        "ruleset_id": ruleset_id,
                        "ruleset_name": ruleset_name,
                        "integration_id": item.get("integration_id"),
                        "app_id": item.get("app_id"),
                        "source": "ruleset",
                    }
                )
    return details


def _check_run_sources(
    repo: str, branch: str, token: str
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """采集最近 commit 的 check-runs 来源 App；失败只记录 warning，不阻断快照。"""
    path = f"/repos/{repo}/commits/{branch}/check-runs?per_page=100"
    try:
        status, payload = _request(path, token)
    except CaptureError as exc:
        return {}, {}, f"check-runs 采集失败: {exc}"
    if status != 200 or not isinstance(payload, dict):
        return {}, payload if isinstance(payload, dict) else {}, f"check-runs 采集失败: HTTP {status}"
    sources: dict[str, Any] = {}
    for run in payload.get("check_runs") or []:
        if not isinstance(run, dict):
            continue
        name = str(run.get("name") or "").strip()
        if not name:
            continue
        app = run.get("app") or {}
        sources[name] = {
            "app_id": app.get("id"),
            "app_slug": app.get("slug"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "head_sha": run.get("head_sha"),
            "html_url": run.get("html_url"),
        }
    return sources, payload, ""


def capture(repo: str, branch: str) -> dict[str, Any]:
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
    if not isinstance(protection, dict):
        protection = {}

    required_checks: list[str] = []
    checks = ((protection or {}).get("required_status_checks") or {}).get("contexts") or []
    required_checks.extend(str(item) for item in checks)
    reviews = (protection or {}).get("required_pull_request_reviews") or {}
    require_pr = bool(reviews)
    require_non_author = bool(reviews.get("require_code_owner_reviews")) if reviews else None
    allow_force_push = ((protection or {}).get("allow_force_pushes") or {}).get("enabled")
    allow_deletions = ((protection or {}).get("allow_deletions") or {}).get("enabled")

    ruleset_summary: list[dict[str, Any]] = []
    ruleset_details: dict[str, Any] = {}
    for item in rulesets or []:
        if not isinstance(item, dict):
            continue
        ruleset_id = item.get("id")
        detail: dict[str, Any] = {}
        if ruleset_id:
            status, payload = _request(f"/repos/{repo}/rulesets/{ruleset_id}", token)
            if status == 200 and isinstance(payload, dict):
                detail = payload
                ruleset_details[str(ruleset_id)] = payload
        rules = detail.get("rules") or []
        types = {str(rule.get("type") or "") for rule in rules if isinstance(rule, dict)}
        if "required_status_checks" in types:
            for rule in rules:
                if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                    continue
                for check in (rule.get("parameters") or {}).get("required_status_checks") or []:
                    context = str((check or {}).get("context") or "").strip()
                    if context:
                        required_checks.append(context)
        if "pull_request" in types:
            require_pr = True
            for rule in rules:
                if not isinstance(rule, dict) or rule.get("type") != "pull_request":
                    continue
                params = rule.get("parameters") or {}
                if bool(params.get("require_code_owner_review")) or int(
                    params.get("required_approving_review_count") or 0
                ) > 0:
                    require_non_author = True
                if require_non_author is None:
                    require_non_author = False
        if "non_fast_forward" in types:
            allow_force_push = False
        if "deletion" in types:
            allow_deletions = False
        ruleset_summary.append(
            {
                "id": ruleset_id,
                "name": item.get("name"),
                "enforcement": item.get("enforcement"),
                "target": item.get("target"),
                "conditions": detail.get("conditions") or item.get("conditions"),
                "rules": rules,
            }
        )

    check_sources, check_runs_snapshot, check_runs_error = _check_run_sources(repo, branch, token)
    captured_at = datetime.now(UTC).isoformat()
    required_checks_detail = _required_check_details(ruleset_summary)
    details_by_context = {
        str(item["context"]): item for item in required_checks_detail if item.get("context")
    }
    warnings: list[str] = []
    for context in REQUIRED_CHECKS:
        detail = details_by_context.get(context)
        if detail is None:
            warnings.append(f"required check {context!r} 尚未出现在任何 ruleset 中")
            continue
        if detail.get("integration_id") is None and detail.get("app_id") is None:
            warnings.append(f"required check {context!r} 的 ruleset 未记录 integration_id/app_id")
    if check_runs_error:
        warnings.append(check_runs_error)

    verified = bool(protection or ruleset_summary)
    return {
        "schema_version": "1.1",
        "repository": repo,
        "branch": branch,
        "verified": verified,
        "checked_at": captured_at,
        "captured_at": captured_at,
        "source": "github-api",
        "reason": "" if verified else "GitHub 未返回 branch protection 或 ruleset 配置",
        "required_checks": sorted(set(required_checks)),
        "required_checks_detail": required_checks_detail,
        "require_pr_before_merge": require_pr or None,
        "require_non_author_review": require_non_author,
        "allow_force_push": allow_force_push,
        "allow_deletions": allow_deletions,
        "ruleset_ids": [item.get("id") for item in ruleset_summary if item.get("id")],
        "rulesets": ruleset_summary,
        "check_sources": check_sources,
        "ruleset_api_snapshot": {
            "captured_at": captured_at,
            "repository": repo,
            "branch": branch,
            "ruleset_ids": [item.get("id") for item in ruleset_summary if item.get("id")],
            "branch_protection": protection,
            "rulesets_list": rulesets,
            "ruleset_details": ruleset_details,
            "check_runs": check_runs_snapshot,
            "check_runs_error": check_runs_error,
        },
        "warnings": warnings,
        "expected_checks": list(REQUIRED_CHECKS),
        "aiqe_aggregate_check": AIQE_AGGREGATE_CHECK,
        "capture_command": (
            f"python scripts/aiqe/check_branch_protection.py --capture --repo {repo} --branch {branch}"
        ),
    }


def _validate_check_sources(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = payload.get("check_sources")
    if sources is None:
        return errors
    if not isinstance(sources, dict):
        return ["check_sources 必须是对象（context -> 来源 App）"]
    for context in REQUIRED_CHECKS:
        raw = sources.get(context)
        if not isinstance(raw, dict):
            continue
        app_id = raw.get("app_id")
        if app_id is None:
            continue
        try:
            app_id_int = int(app_id)
        except (TypeError, ValueError):
            errors.append(f"{context}: check source app id 非法: {app_id!r}")
            continue
        if app_id_int not in TRUSTED_APPS:
            errors.append(
                f"{context}: check source App {app_id_int} 不可信"
                f"（只接受 GitHub Actions {sorted(TRUSTED_APPS)}）"
            )
    return errors


def validate(payload: Any) -> list[str]:
    """精确校验 required contexts 与证据完整性；返回错误列表（空 = 通过）。"""
    if not isinstance(payload, dict):
        return ["缺少 branch-protection.json（证据必须是 JSON 对象）"]
    check = validate_branch_protection(payload)
    errors: list[str] = [] if check.status == "PASS" else [str(item) for item in check.reasons]
    errors.extend(_validate_check_sources(payload))
    deduped: list[str] = []
    for error in errors:
        if error not in deduped:
            deduped.append(error)
    return deduped


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
        printed = target.relative_to(ROOT) if target.is_relative_to(ROOT) else target
        print(f"written {printed}")
        for warning in payload.get("warnings") or []:
            print(f"::warning::[branch-protection] {warning}")
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
        print(
            json.dumps(
                {
                    "ok": True,
                    "repository": payload.get("repository"),
                    "ruleset_ids": payload.get("ruleset_ids"),
                    "required_checks": payload.get("required_checks"),
                    "aiqe_aggregate_check": AIQE_AGGREGATE_CHECK,
                },
                ensure_ascii=False,
            )
        )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
