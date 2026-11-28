"""记录 V16-025 / FIX-014 独立验收（人工签署 + 真实 GitHub Reviewer 身份）。

用法
----
    # REVIEWED（角色域模式）：需要人工评审记录 artifact（仓库内路径）
    python scripts/aiqe/record_acceptance.py \
        --requirement V16-001-R1 \
        --reviewer qa-lead \
        --reviewed-at 2026-11-24 \
        --artifact docs/aiqe/v1.6/acceptance/reviews/V16-001-R1-qa-lead.md \
        --decision REVIEWED

    # GA 模式（推荐）：绑定真实 GitHub Review 身份，缺字段直接拒绝
    python scripts/aiqe/record_acceptance.py --requirement V16-001-R1 \
        --reviewer qa-lead --reviewed-at 2026-11-26 \
        --artifact docs/aiqe/v1.6/acceptance/reviews/V16-001-R1-MoojinR.md \
        --decision REVIEWED \
        --reviewer-login MoojinR --reviewer-user-id 1234567 \
        --pr-number 641 --review-id 987654321 \
        --reviewed-commit-sha <current-head-sha> --review-state APPROVED \
        --review-submitted-at 2026-11-26T10:00:00Z \
        --expected-commit <current-head-sha> --author-user-id <owner-github-id> \
        --require-github-identity --verify-online

    # WAIVED：需要 waiver 理由与批准人
    python scripts/aiqe/record_acceptance.py \
        --requirement TC-AIQE-010 --reviewer qa-lead --reviewed-at 2026-11-24 \
        --decision WAIVED --waiver-reason "无 30+ 标注样本，用户暂缓" --waived-by user

记录写入 ``docs/aiqe/v1.6/acceptance/records/<REQ-ID>.json``；
``check_traceability.py`` 与 ``release_verdict.py`` 会把合法记录合并进矩阵。

FIX-014 约束：
- ``--reviewer`` / ``--reviewer-role`` 只是**职责标签**，不是身份认证；
- ``--require-github-identity``（GA 模式）要求 reviewer_login / user id / PR /
  review id / review state=APPROVED / reviewed commit SHA / review submitted_at，
  且 reviewer 与 owner 的 GitHub user id 必须不同、review 必须指向当前 HEAD；
- ``--verify-online`` 额外调用 GitHub API 回查 review；网络/令牌缺失时明确
  **BLOCKED** 并拒绝写入，绝不静默通过；
- 禁止：reviewer=pending、Owner 自审、reviewer 角色域与 owner 相同、artifact 不存在、
  伪造 review 字段或改写历史记录。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(SCRIPT_DIR))
from acceptance_records import (  # noqa: E402
    IDENTITY_FIELDS,
    RECORDS_DIR,
    load_role_matrix,
    validate_record,
)

MATRIX = ROOT / "docs/aiqe/v1.6/traceability/requirements.yaml"
DEFAULT_REPO = "mojinru9527/cameltv-test-platform"


def _entry(requirement_id: str) -> dict | None:
    document = yaml.safe_load(MATRIX.read_text(encoding="utf-8")) or {}
    for entry in document.get("requirements") or []:
        if str(entry.get("id")) == requirement_id:
            return entry
    return None


def _identity_payload(args: argparse.Namespace) -> dict[str, object]:
    mapping = {
        "reviewer_login": args.reviewer_login,
        "reviewer_user_id": args.reviewer_user_id,
        "pr_number": args.pr_number,
        "review_id": args.review_id,
        "reviewed_commit_sha": args.reviewed_commit_sha,
        "review_state": args.review_state,
        "review_submitted_at": args.review_submitted_at,
    }
    payload: dict[str, object] = {}
    for key, value in mapping.items():
        if value is None or str(value).strip() == "":
            continue
        payload[key] = value
    return payload


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover - 非标准流
            pass
    parser = argparse.ArgumentParser(description="记录 AIQE V1.6 独立验收")
    parser.add_argument("--requirement", required=True)
    # 兼容旧参数：reviewer 是职责标签，不是真实 GitHub 身份。
    parser.add_argument("--reviewer", required=True, help="职责标签（如 qa-lead）")
    parser.add_argument("--reviewer-role", default="", help="角色域（缺省按 review-roles.yaml）")
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--artifact", default="")
    parser.add_argument("--decision", choices=("REVIEWED", "WAIVED"), required=True)
    parser.add_argument("--waiver-reason", default="")
    parser.add_argument("--waived-by", default="")
    parser.add_argument(
        "--reviewer-login", default="", help="真实 GitHub login（FIX-014）"
    )
    parser.add_argument("--reviewer-user-id", type=int, default=None, help="GitHub numeric user id")
    parser.add_argument("--pr-number", type=int, default=None, help="审批所在的 PR number")
    parser.add_argument("--review-id", type=int, default=None, help="GitHub review id")
    parser.add_argument("--reviewed-commit-sha", default="", help="review 指向的 commit SHA")
    parser.add_argument("--review-state", default="", help="GitHub review state（必须 APPROVED）")
    parser.add_argument("--review-submitted-at", default="", help="review 提交时间（ISO8601）")
    parser.add_argument(
        "--require-github-identity",
        action="store_true",
        help="GA 模式：必须绑定真实 GitHub Review 身份，缺字段拒绝",
    )
    parser.add_argument(
        "--verify-online",
        action="store_true",
        help="调用 GitHub API 回查 review（需要 GITHUB_TOKEN；不可用时 BLOCKED）",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--expected-commit", default="", help="当前 HEAD；用于 stale review 校验")
    parser.add_argument("--author-user-id", type=int, default=None, help="作者 owner 的 GitHub user id")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--records-dir", default=str(RECORDS_DIR))
    args = parser.parse_args(argv)

    entry = _entry(args.requirement)
    if entry is None:
        print(f"::error::[acceptance] 追踪矩阵中不存在需求: {args.requirement}")
        return 1
    record: dict[str, object] = {
        "requirement_id": args.requirement,
        "decision": args.decision,
        "reviewer": args.reviewer,
        "reviewed_at": args.reviewed_at,
        "artifact": args.artifact,
    }
    if args.reviewer_role:
        record["reviewer_role"] = args.reviewer_role
    record.update(_identity_payload(args))
    if args.decision == "WAIVED":
        record["waiver_reason"] = args.waiver_reason
        record["waived_by"] = args.waived_by

    require_identity = bool(args.require_github_identity or args.verify_online)
    if require_identity and not args.expected_commit.strip():
        print(
            "::error::[acceptance] GA 模式必须提供 --expected-commit（当前 HEAD）："
            "否则无法识别 stale review，review 不能证明批准的是当前 commit"
        )
        return 1
    errors = validate_record(
        record,
        requirement_id=args.requirement,
        owner=str(entry.get("owner") or ""),
        roles=load_role_matrix(),
        require_github_identity=args.require_github_identity,
        expected_commit=args.expected_commit,
        author_user_id=args.author_user_id,
        verify_online=args.verify_online,
        repo=args.repo,
    )
    if errors:
        for error in errors:
            print(f"::error::[acceptance] {error}")
        if args.verify_online:
            print(
                "::error::[acceptance] 无法在线回查 GitHub Reviewer 身份：记录状态 BLOCKED，"
                "不得写入 REVIEWED"
            )
        return 1
    records_dir = Path(args.records_dir)
    target = records_dir / f"{args.requirement}.json"
    if target.exists() and not args.force:
        print(f"::error::[acceptance] 记录已存在（需 --force 覆盖）: {target}")
        return 1
    records_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    identity_mode = (
        "GITHUB_REVIEW_ONLINE_VERIFIED"
        if args.verify_online
        else "GITHUB_REVIEW_REQUIRED"
        if require_identity
        else "ROLE_LABEL_ONLY"
    )
    print(
        json.dumps(
            {
                "written": target.relative_to(ROOT).as_posix()
                if target.is_relative_to(ROOT)
                else str(target),
                "requirement": args.requirement,
                "decision": args.decision,
                "reviewer": args.reviewer,
                "identity_mode": identity_mode,
                "identity_fields": [key for key in IDENTITY_FIELDS if key in record],
                "note": "请运行 check_traceability.py --strict-warnings 与 "
                "release_verdict.py --write 重算判定；记录需随 PR 提交。",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
