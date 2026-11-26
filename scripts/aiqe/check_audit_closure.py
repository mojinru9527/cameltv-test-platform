"""V1.6 外部审计整改台账校验与报告生成（P0/P1/P2 全量可追溯）。

规则
----
- ``CLOSED``：evidence 至少一项且全部路径存在；禁止空证据。
- ``EXTERNAL``：必须写 ``blocked_by`` / ``owner`` / ``unblock_action``。
- 台账必须覆盖下方 ``REQUIRED_IDS``（防止悄悄删条目）。
- ``--check``：校验 + 生成型报告新鲜度（与 ``--write`` 输出一致）。

用法
----
    python scripts/aiqe/check_audit_closure.py --check
    python scripts/aiqe/check_audit_closure.py --write
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
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


def _path_exists(raw: str) -> bool:
    text = str(raw or "").replace("\\", "/").strip()
    return bool(text) and (ROOT / text).exists()


def load_ledger(path: Path = LEDGER) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate(ledger: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    items = ledger.get("items") or []
    seen: set[str] = set()
    for item in items:
        item_id = str(item.get("id") or "?")
        if item_id in seen:
            errors.append(f"{item_id}: 重复条目")
        seen.add(item_id)
        status = str(item.get("status") or "").upper()
        if status not in STATUSES:
            errors.append(f"{item_id}: 非法 status {status!r}（允许 {sorted(STATUSES)}）")
            continue
        if not str(item.get("title") or "").strip():
            errors.append(f"{item_id}: 缺少 title")
        evidence = item.get("evidence") or []
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{item_id}: 缺少 evidence")
            evidence = []
        for path in evidence:
            if not _path_exists(str(path)):
                errors.append(f"{item_id}: evidence 路径不存在: {path}")
        if status == "CLOSED" and not evidence:
            errors.append(f"{item_id}: CLOSED 必须有 evidence")
        if status == "EXTERNAL":
            for field in EXTERNAL_FIELDS:
                if not str(item.get(field) or "").strip():
                    errors.append(f"{item_id}: EXTERNAL 必须填写 {field}")
            if not evidence:
                errors.append(f"{item_id}: EXTERNAL 仍需给出已落地的证据/机制路径")
        if status == "CLOSED" and str(item.get("note") or "").strip() == "":
            errors.append(f"{item_id}: CLOSED 建议写 note（做了什么）")
    for required in REQUIRED_IDS:
        if required not in seen:
            errors.append(f"台账缺少审计条目: {required}")
    return errors


def render(ledger: dict[str, Any]) -> str:
    items = list(ledger.get("items") or [])
    closed = [item for item in items if str(item.get("status")).upper() == "CLOSED"]
    external = [item for item in items if str(item.get("status")).upper() == "EXTERNAL"]
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
        f"| CLOSED（机制/代码/测试已落地） | {len(closed)} |",
        f"| EXTERNAL（需环境/权限/人工） | {len(external)} |",
        f"| **合计** | **{len(items)}** |",
        "",
        "## 逐项状态",
        "",
        "| ID | 审计发现 | 状态 | 已落地证据 | 外部条件（EXTERNAL） |",
        "|---|---|---|---|---|",
    ]
    for item in items:
        evidence = "<br>".join(f"`{path}`" for path in item.get("evidence") or [])
        if str(item.get("status")).upper() == "EXTERNAL":
            external_text = (
                f"blocked_by: {item.get('blocked_by')}<br>"
                f"owner: {item.get('owner')}<br>"
                f"unblock: {item.get('unblock_action')}"
            )
        else:
            external_text = "—"
        lines.append(
            f"| {item.get('id')} | {item.get('title')} | **{item.get('status')}** | "
            f"{evidence or '—'} | {external_text} |"
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- CLOSED 不等于 GA 通过：独立验收、产品级 E2E、Branch Protection、")
    lines.append("  生产证据仍是 EXTERNAL，机器判定以 `release-verdict.json` 为准。")
    if external:
        lines.append("- EXTERNAL 项必须由对应 owner 完成后才能重算 Gate 与 GA 状态。")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计整改台账校验/报告生成")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--ledger", default=str(LEDGER))
    parser.add_argument("--report", default=str(REPORT))
    args = parser.parse_args(argv)

    ledger = load_ledger(Path(args.ledger))
    errors = validate(ledger)
    if args.write:
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(ledger) + "\n", encoding="utf-8", newline="\n")
        print(f"written {target}")
    else:
        target = Path(args.report)
        if not target.exists():
            errors.append(f"缺少审计整改报告: {target}")
        elif target.read_text(encoding="utf-8") != render(ledger) + "\n":
            errors.append("V1.6.1-Audit-Closure-Report.md 与台账生成结果不一致（请 --write）")
    for error in errors:
        print(f"::error::[audit-closure] {error}")
    counts = {
        "closed": sum(1 for item in ledger.get("items") or [] if str(item.get("status")).upper() == "CLOSED"),
        "external": sum(
            1 for item in ledger.get("items") or [] if str(item.get("status")).upper() == "EXTERNAL"
        ),
        "errors": len(errors),
    }
    print(counts)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
