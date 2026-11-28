"""V1.6 外部审计整改台账校验与报告生成（FIX-012：语义证据验证）。

规则
----
- 每个条目必须声明 ``closure_rule_id``，且该规则必须在
  ``validators.closure_rules`` 注册表中真实存在。
- ``CLOSED`` 必须同时满足：语义规则 ``PASS`` + 真实 ``verified_commit_sha`` +
  可执行 verifier（名称/版本/CI Run）+ artifact hash（与文件实际 sha256 一致）+
  ``verified_at`` + 真实 GitHub review（reviewer_login/review_id/reviewed_commit_sha）。
  缺 review 的条目必须降级 ``EXTERNAL``，不得保留假 CLOSED。
- ``EXTERNAL`` 必须写 ``downgrade_reason`` / ``blocked_by`` / ``owner`` /
  ``unblock_action``，说明为什么不能关闭以及谁在什么条件下可以解除。
- 台账必须覆盖 ``REQUIRED_IDS``（防止悄悄删条目）。
- ``--check``：结构校验 + 所有 CLOSED 的语义验证 + 生成型报告新鲜度；
  任一 CLOSED 未通过语义验证即非零退出。``--write`` 重新生成报告。

用法
----
    python scripts/aiqe/check_audit_closure.py --check
    python scripts/aiqe/check_audit_closure.py --write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover - 脚本/测试两条加载路径
    sys.path.insert(0, str(SCRIPT_DIR))
from validators.closure_rules import (  # noqa: E402
    RULES,
    RuleOutcome,
    get_rule,
    verify_item,
)
from validators.common import is_sha, parse_time, resolve_repo_path, sha256_file  # noqa: E402

LEDGER = ROOT / "docs/aiqe/v1.6/governance/audit-closure.yaml"
REPORT = ROOT / "docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md"

REQUIRED_IDS = (
    "P0-1",
    "P0-2",
    "P0-3",
    "P0-4",
    "P1-1",
    "P1-2",
    "P1-3",
    "P1-4",
    "P1-5",
    "P1-6",
    "P1-7",
    "P1-8",
    "P1-9",
    "P1-10",
    "P2-1",
    "P2-2",
    "P2-3",
    "P2-4",
    "P3-1",
)
STATUSES = {"CLOSED", "EXTERNAL"}
EXTERNAL_FIELDS = ("blocked_by", "owner", "unblock_action")
REVIEW_FIELDS = ("reviewer_login", "review_id", "reviewed_commit_sha")
VERIFIER_FIELDS = ("name", "version", "ci_run_id")


def _status(item: dict[str, Any]) -> str:
    return str(item.get("status") or "").strip().upper()


def _path_exists(root: Path, raw: object) -> bool:
    path = resolve_repo_path(root, raw)
    return path is not None and path.exists()


def _iter_items(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    items = ledger.get("items") or []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def load_ledger(path: Path = LEDGER) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _validate_closed(
    item: dict[str, Any],
    evidence: list[Any],
    errors: list[str],
    *,
    root: Path,
) -> None:
    item_id = str(item.get("id") or "?")
    verified_sha = str(item.get("verified_commit_sha") or "").strip().lower()
    if not is_sha(verified_sha):
        errors.append(f"{item_id}: CLOSED 必须有 40 位 verified_commit_sha")
    verifier = item.get("verifier") if isinstance(item.get("verifier"), dict) else {}
    for field in VERIFIER_FIELDS:
        if str(verifier.get(field) or "").strip() == "":
            errors.append(f"{item_id}: CLOSED 的 verifier 必须填写 {field}")
    artifact_hashes = item.get("artifact_hashes") if isinstance(item.get("artifact_hashes"), dict) else {}
    if not artifact_hashes:
        errors.append(f"{item_id}: CLOSED 必须记录 artifact_hashes（证据 sha256）")
    else:
        for raw in evidence:
            path = resolve_repo_path(root, raw)
            if path is None or not path.is_file():
                continue
            key = str(raw).replace("\\", "/").strip()
            recorded = str(
                artifact_hashes.get(key)
                or artifact_hashes.get(str(raw))
                or artifact_hashes.get(key.removeprefix("./"))
                or ""
            ).strip().lower().removeprefix("sha256:")
            if not recorded:
                errors.append(f"{item_id}: CLOSED 的 artifact_hashes 缺少证据 {key}")
            elif recorded != sha256_file(path):
                errors.append(f"{item_id}: CLOSED 的 artifact_hashes 与 {key} 实际 sha256 不一致")
    if parse_time(item.get("verified_at")) is None:
        errors.append(f"{item_id}: CLOSED 必须有可解析的 verified_at")
    review = item.get("review") if isinstance(item.get("review"), dict) else {}
    missing_review = [
        field for field in REVIEW_FIELDS if str(review.get(field) or "").strip() == ""
    ]
    if missing_review:
        errors.append(
            f"{item_id}: CLOSED 必须有真实 GitHub review（缺 {missing_review}）；"
            "没有真实 review 的条目必须留空 review 并降级为 EXTERNAL"
        )
    else:
        reviewed_sha = str(review.get("reviewed_commit_sha") or "").strip().lower()
        if is_sha(verified_sha) and reviewed_sha != verified_sha:
            errors.append(
                f"{item_id}: review.reviewed_commit_sha 与 verified_commit_sha 不一致"
            )
    if not str(item.get("note") or "").strip():
        errors.append(f"{item_id}: CLOSED 必须写 note（做了什么、验证器结论）")
    if not evidence:
        errors.append(f"{item_id}: CLOSED 必须有 evidence")


def validate(ledger: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    """台账结构与关闭记录完整性校验（不执行语义规则，见 verify_closed）。"""
    errors: list[str] = []
    items = _iter_items(ledger)
    if not items:
        errors.append("台账没有 items")
    seen: set[str] = set()
    for item in items:
        item_id = str(item.get("id") or "?")
        if item_id in seen:
            errors.append(f"{item_id}: 重复条目")
        seen.add(item_id)
        status = _status(item)
        if status not in STATUSES:
            errors.append(f"{item_id}: 非法 status {status!r}（允许 {sorted(STATUSES)}）")
            continue
        if not str(item.get("title") or "").strip():
            errors.append(f"{item_id}: 缺少 title")
        issue_id = str(item.get("issue_id") or "").strip()
        if not issue_id:
            errors.append(f"{item_id}: 缺少 issue_id")
        elif issue_id != item_id:
            errors.append(f"{item_id}: issue_id={issue_id!r} 与台账 id 不一致")
        rule_id = str(item.get("closure_rule_id") or "").strip()
        if not rule_id:
            errors.append(f"{item_id}: 缺少 closure_rule_id")
        elif get_rule(rule_id) is None:
            errors.append(f"{item_id}: closure_rule_id 未注册: {rule_id!r}")
        verdict = str(item.get("rule_verdict") or "").strip().upper()
        if verdict:
            if verdict not in {"PASS", "FAIL", "NOT_PROVEN"}:
                errors.append(f"{item_id}: rule_verdict 非法 {verdict!r}")
            if parse_time(item.get("rule_checked_at")) is None:
                errors.append(f"{item_id}: 有 rule_verdict 时必须写可解析的 rule_checked_at")
        evidence = item.get("evidence") or []
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{item_id}: 缺少 evidence")
            evidence = []
        for path in evidence:
            if not _path_exists(root, path):
                errors.append(f"{item_id}: evidence 路径不存在: {path}")
        if status == "CLOSED":
            _validate_closed(item, list(evidence), errors, root=root)
        elif status == "EXTERNAL":
            for field in EXTERNAL_FIELDS:
                if not str(item.get(field) or "").strip():
                    errors.append(f"{item_id}: EXTERNAL 必须填写 {field}")
            if not str(item.get("downgrade_reason") or "").strip():
                errors.append(
                    f"{item_id}: EXTERNAL 必须填写 downgrade_reason（为什么不能 CLOSED）"
                )
    for required in REQUIRED_IDS:
        if required not in seen:
            errors.append(f"台账缺少审计条目: {required}")
    return errors


def verify_closed(
    ledger: dict[str, Any],
    *,
    root: Path = ROOT,
    expected_commit: str = "",
) -> tuple[list[str], list[tuple[dict[str, Any], RuleOutcome]]]:
    """对所有 CLOSED 条目执行语义规则；EXTERNAL 条目也计算规则结论供复核。"""
    errors: list[str] = []
    outcomes: list[tuple[dict[str, Any], RuleOutcome]] = []
    for item in _iter_items(ledger):
        item_id = str(item.get("id") or "?")
        outcome = verify_item(item, root=root, expected_commit=expected_commit)
        outcomes.append((item, outcome))
        if _status(item) != "CLOSED":
            continue
        if not outcome.passed:
            detail = "；".join(outcome.reasons[:6]) or "规则未通过"
            errors.append(
                f"{item_id}: CLOSED 未通过语义验证（{outcome.rule_id} → {outcome.status}）: {detail}"
            )
        declared_verdict = str(item.get("rule_verdict") or "").strip().upper()
        if declared_verdict and declared_verdict != outcome.status:
            errors.append(
                f"{item_id}: CLOSED 的 rule_verdict={declared_verdict} 与本次语义验证 "
                f"{outcome.status} 不一致"
            )
        verified_sha = str(item.get("verified_commit_sha") or "").strip().lower()
        if expected_commit and verified_sha and verified_sha != expected_commit.strip().lower():
            errors.append(
                f"{item_id}: CLOSED 的 verified_commit_sha={verified_sha[:12]} 不是当前验收 SHA "
                f"{expected_commit.strip().lower()[:12]}"
            )
    return errors, outcomes


def _md(text: object) -> str:
    return str(text if text is not None else "—").replace("|", "/").replace("\n", "<br>")


def render(ledger: dict[str, Any]) -> str:
    items = _iter_items(ledger)
    closed = [item for item in items if _status(item) == "CLOSED"]
    external = [item for item in items if _status(item) == "EXTERNAL"]
    lines = [
        "# V1.6 外部审计整改报告（机器生成）",
        "",
        "> 本文件由 `python scripts/aiqe/check_audit_closure.py --write` 从",
        "> `governance/audit-closure.yaml` 生成，**禁止手工编辑**。",
        f"> 审计对象：`{ledger.get('audit')}`（{ledger.get('audit_date')}）",
        f"> 基线 commit：`{ledger.get('baseline_commit')}`",
        "",
        "## 汇总",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
        f"| CLOSED（语义规则通过且真实 review 齐备） | {len(closed)} |",
        f"| EXTERNAL（语义规则不通过或缺真实 review） | {len(external)} |",
        f"| **合计** | **{len(items)}** |",
        "",
        "## 关闭规则注册表",
        "",
        "| 规则 | 验证器 | 版本 | 说明 | 使用条目数 |",
        "|---|---|---|---|---:|",
    ]
    usage: dict[str, int] = {}
    for item in items:
        rule_id = str(item.get("closure_rule_id") or "")
        usage[rule_id] = usage.get(rule_id, 0) + 1
    for rule in RULES.values():
        lines.append(
            f"| `{rule.rule_id}` | {rule.verifier_name} | {rule.verifier_version} | "
            f"{_md(rule.description)} | {usage.get(rule.rule_id, 0)} |"
        )
    for rule_id in sorted(key for key in usage if key not in RULES):
        lines.append(f"| `{rule_id or '<missing>'}` | <unregistered> | <unregistered> | — | {usage[rule_id]} |")
    lines.extend(
        [
            "",
            "## 逐项语义审计",
            "",
            "| ID | issue_id | 需求条目 | 审计发现 | 状态 | 关闭规则 | 规则结论 | 验证器 "
            "| 已验证 SHA | 证据 hash | 已落地证据 | 未通过原因 / 外部条件 |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in items:
        item_id = str(item.get("id") or "?")
        rule_id = str(item.get("closure_rule_id") or "")
        rule = get_rule(rule_id)
        verifier = (
            f"{rule.verifier_name}@{rule.verifier_version}"
            if rule is not None
            else "<unregistered>"
        )
        verdict = str(item.get("rule_verdict") or "—").strip().upper() or "—"
        verified_sha = str(item.get("verified_commit_sha") or "").strip()
        hashes = item.get("artifact_hashes") if isinstance(item.get("artifact_hashes"), dict) else {}
        hash_text = (
            "<br>".join(
                f"`{Path(str(path)).name}`={str(digest)[:12]}"
                for path, digest in sorted(hashes.items())[:4]
            )
            or "—"
        )
        evidence_text = "<br>".join(f"`{path}`" for path in item.get("evidence") or []) or "—"
        if _status(item) == "CLOSED":
            reason_text = "—"
        else:
            reason_text = (
                f"downgrade: {_md(item.get('downgrade_reason'))}<br>"
                f"blocked_by: {_md(item.get('blocked_by'))}<br>"
                f"owner: {_md(item.get('owner'))}<br>"
                f"unblock: {_md(item.get('unblock_action'))}"
            )
        lines.append(
            f"| {item_id} | {_md(item.get('issue_id'))} | {_md(item.get('requirement_id'))} | "
            f"{_md(item.get('title'))} | **{_md(item.get('status'))}** | `{rule_id or '—'}` | "
            f"**{verdict}** | {verifier} | `{verified_sha or '—'}` | {hash_text} | "
            f"{evidence_text} | {reason_text} |"
        )
    lines.extend(
        [
            "",
            "## 关闭口径（V1.6.2 / FIX-012）",
            "",
            "- `CLOSED` 只能由 `closure_rule_id` 对应的语义验证器证明：产品 TC 必须读取",
            "  runner/结果/断言/artifact/SHA 并与 matrix 一致；Runtime Index 必须逐条可追溯；",
            "  凭据扫描必须是当前 SHA；Ruleset 必须精确包含 AIQE 聚合 Gate。",
            "- `CLOSED` 还必须绑定真实 `verified_commit_sha`、verifier（名称/版本/CI Run）、",
            "  artifact hash、`verified_at` 与真实 GitHub review（reviewer_login/review_id/",
            "  reviewed_commit_sha）。没有真实 review 的条目一律留空 review 并降级 `EXTERNAL`。",
            "- `EXTERNAL` 不是通过，必须写 `downgrade_reason` / `blocked_by` / `owner` /",
            "  `unblock_action`；解除后重新运行 `--check` 才能恢复 `CLOSED`。",
            "- 语义规则的实时结论由 `python scripts/aiqe/check_audit_closure.py --check --json`",
            "  输出（含每条规则的 conflict/gap 明细）。",
            "",
            "## 说明",
            "",
            "- CLOSED 不等于 GA 通过：独立验收、产品级 E2E、Branch Protection、生产证据仍以",
            "  `scripts/aiqe/release_verdict.py` 的机器判定为准。",
            "- 本报告不含时间戳；`--check` 会逐字节比对生成结果，手工编辑会失败。",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计整改台账校验/报告生成")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--ledger", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--expected-commit",
        default="",
        help="当前验收 SHA；提供后 CLOSED 的 verified_commit_sha 必须与之一致",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    ledger_path = Path(args.ledger) if args.ledger else root / "docs/aiqe/v1.6/governance/audit-closure.yaml"
    report_path = Path(args.report) if args.report else root / "docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md"
    ledger = load_ledger(ledger_path)
    errors = validate(ledger, root=root)
    semantic_errors, outcomes = verify_closed(
        ledger, root=root, expected_commit=args.expected_commit
    )
    errors.extend(semantic_errors)
    if args.write:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render(ledger) + "\n", encoding="utf-8", newline="\n")
        print(f"written {report_path}")
    else:
        if not report_path.exists():
            errors.append(f"缺少审计整改报告: {report_path}")
        elif report_path.read_text(encoding="utf-8") != render(ledger) + "\n":
            errors.append(
                "V1.6.1-Audit-Closure-Report.md 与台账生成结果不一致（请 --write）"
            )
    for error in errors:
        print(f"::error::[audit-closure] {error}")
    closed = sum(1 for item in _iter_items(ledger) if _status(item) == "CLOSED")
    external = sum(1 for item in _iter_items(ledger) if _status(item) == "EXTERNAL")
    print({"closed": closed, "external": external, "errors": len(errors)})
    if args.json:
        print(
            json.dumps(
                {
                    "closed": closed,
                    "external": external,
                    "errors": errors,
                    "rule_verdicts": [
                        {
                            "id": str(item.get("id")),
                            "status": _status(item),
                            "closure_rule_id": outcome.rule_id,
                            "rule_status": outcome.status,
                            "conflicts": outcome.conflicts,
                            "gaps": outcome.gaps,
                        }
                        for item, outcome in outcomes
                    ],
                },
                ensure_ascii=False,
            )
        )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
