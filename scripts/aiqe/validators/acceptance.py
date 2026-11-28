"""验收记录 GitHub 身份校验（FIX-014）。

角色别名（qa/security）只能作为职责标签，不能作为身份认证。ACCEPTED 必须绑定：
真实 GitHub login + numeric user id + PR + review id + reviewed commit + APPROVED 状态。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

from validators.common import is_sha, parse_time
from validators.models import GateCheck

GITHUB_API = "https://api.github.com"
REQUIRED_IDENTITY_FIELDS = (
    "reviewer_login",
    "reviewer_user_id",
    "pr_number",
    "review_id",
    "reviewed_commit_sha",
)


def validate_acceptance_identity(
    record: Any,
    *,
    expected_commit: str = "",
    author_user_id: int | None = None,
    require_identity: bool = True,
) -> GateCheck:
    check = GateCheck()
    if not isinstance(record, dict):
        return GateCheck.unproven("acceptance record 必须是对象")
    status = str(record.get("decision") or record.get("status") or "").upper()
    if status == "WAIVED":
        for field in ("waiver_reason", "waived_by", "waiver_expires_at", "approved_by"):
            if not str(record.get(field) or "").strip():
                check.add(f"WAIVED 缺少 {field}")
        check.add("WAIVED 不等于验收通过", demote_to="NOT_PROVEN")
        return check
    if status != "REVIEWED":
        return GateCheck.unproven(f"decision={status or '<empty>'}，不是 REVIEWED")
    if not require_identity:
        return GateCheck.ok("legacy 角色域校验（非 GA 模式）")

    for field in REQUIRED_IDENTITY_FIELDS:
        if str(record.get(field) or "").strip() == "":
            check.add(f"缺少 GitHub 身份字段 {field}")
    login = str(record.get("reviewer_login") or "").strip()
    if login and not login.replace("-", "").replace("_", "").isalnum():
        check.add(f"reviewer_login 非法: {login!r}")
    try:
        reviewer_id = int(record.get("reviewer_user_id"))
    except (TypeError, ValueError):
        reviewer_id = -1
    if reviewer_id <= 0:
        check.add("reviewer_user_id 必须是真实 GitHub numeric user id")
    if author_user_id is not None and reviewer_id == int(author_user_id):
        check.add("Reviewer 与作者/实现者为同一 GitHub user id，不构成独立验收")
    commit = str(record.get("reviewed_commit_sha") or "").strip().lower()
    if not is_sha(commit):
        check.add("reviewed_commit_sha 非法")
    elif expected_commit and commit != expected_commit.strip().lower():
        check.add(f"reviewed_commit_sha={commit[:12]} 不是当前 HEAD {expected_commit[:12]}（stale review）")
    state = str(record.get("review_state") or "").upper()
    if state != "APPROVED":
        check.add(f"review_state={state or '<empty>'}，必须为 APPROVED")
    if parse_time(record.get("review_submitted_at") or record.get("reviewed_at")) is None:
        check.add("缺少可解析的 review_submitted_at/reviewed_at")
    try:
        if int(record.get("pr_number")) <= 0:
            check.add("pr_number 必须为正整数")
    except (TypeError, ValueError):
        check.add("pr_number 必须是正整数")
    if check.reasons:
        return check
    check.status = "PASS"
    check.note(
        f"验收记录绑定真实 GitHub review {record.get('review_id')} "
        f"({login}#{reviewer_id}) @ {commit[:12]}"
    )
    return check


def fetch_github_review(
    repo: str,
    pr_number: int,
    review_id: int,
    *,
    token: str | None = None,
    opener: Callable[[urllib.request.Request], Any] | None = None,
) -> dict[str, Any]:
    """从 GitHub API 查询 review 原始记录。"""
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("缺少 GITHUB_TOKEN/GH_TOKEN，无法在线核验 Reviewer 身份")
    request = urllib.request.Request(
        f"{GITHUB_API}/repos/{repo}/pulls/{int(pr_number)}/reviews/{int(review_id)}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cameltv-aiqe-acceptance",
        },
    )
    try:
        if opener is not None:
            response = opener(request)
            body = response.read() if hasattr(response, "read") else response
        else:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"查询 GitHub review 失败: HTTP {exc.code}") from exc
    payload = json.loads(body.decode("utf-8") if isinstance(body, bytes) else body)
    return payload if isinstance(payload, dict) else {}


def verify_github_identity(
    record: dict[str, Any],
    *,
    repo: str,
    token: str | None = None,
    opener: Callable[[urllib.request.Request], Any] | None = None,
    expected_commit: str = "",
    author_user_id: int | None = None,
) -> GateCheck:
    check = validate_acceptance_identity(
        record, expected_commit=expected_commit, author_user_id=author_user_id
    )
    if check.status != "PASS":
        return check
    try:
        review = fetch_github_review(
            repo, int(record["pr_number"]), int(record["review_id"]), token=token, opener=opener
        )
    except RuntimeError as exc:
        return GateCheck.unproven(str(exc))
    remote_state = str(review.get("state") or "").upper()
    remote_commit = str(review.get("commit_id") or "").lower()
    remote_user = review.get("user") or {}
    remote_id = int(remote_user.get("id") or -1)
    if remote_state != "APPROVED":
        check.add(f"GitHub review 实际状态为 {remote_state}")
    if remote_commit != str(record.get("reviewed_commit_sha") or "").lower():
        check.add("GitHub review commit 与记录不一致")
    if remote_id != int(record.get("reviewer_user_id") or -1):
        check.add("GitHub review user id 与记录不一致")
    if str(remote_user.get("login") or "") != str(record.get("reviewer_login") or ""):
        check.add("GitHub review login 与记录不一致")
    return check


__all__ = [
    "REQUIRED_IDENTITY_FIELDS",
    "fetch_github_review",
    "validate_acceptance_identity",
    "verify_github_identity",
]
