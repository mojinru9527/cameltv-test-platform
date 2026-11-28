"""FIX-015：生成 V1.6.2 Hardening 最终验收报告（机器事实 + 人工 disposition）。

报告不是自评：Gate / Product TC / GA 状态全部来自 release-verdict.json 与
product-results.json；FIX-001..015 的 VERIFIED/PARTIAL/BLOCKED 判断来自
``governance/v162-fix-disposition.yaml``，且必须给出证据或阻塞原因。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/aiqe/v1.6"
DEFAULT_DISPOSITION = DOCS / "governance/v162-fix-disposition.yaml"
DEFAULT_OUTPUT = DOCS / "V1.6.2-Hardening-Final-Acceptance.md"
FIX_IDS = tuple(f"FIX-{index:03d}" for index in range(1, 16))
ALLOWED = {"VERIFIED", "PARTIAL", "BLOCKED"}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_report(root: Path, *, disposition_path: Path | None = None) -> tuple[str, dict[str, Any]]:
    docs = root / "docs/aiqe/v1.6"
    verdict = _load_json(docs / "release-verdict.json")
    product = _load_json(docs / "e2e/product-results.json")
    disposition = _load_yaml(disposition_path or docs / "governance/v162-fix-disposition.yaml")
    items = {str(item.get("fix")): item for item in disposition.get("fixes") or []}
    errors: list[str] = []
    for fix_id in FIX_IDS:
        if fix_id not in items:
            errors.append(f"{fix_id}: disposition 缺少条目")
            continue
        status = str(items[fix_id].get("status") or "").upper()
        if status not in ALLOWED:
            errors.append(f"{fix_id}: 非法状态 {status}")
        if status == "VERIFIED" and not items[fix_id].get("evidence"):
            errors.append(f"{fix_id}: VERIFIED 必须给出 evidence")
        if status in {"PARTIAL", "BLOCKED"} and not items[fix_id].get("reason"):
            errors.append(f"{fix_id}: {status} 必须给出 reason")

    gates = verdict.get("gates") or {}
    product_tests = {str(item.get("tc_id")): item for item in product.get("tests") or []}
    ga_ready = bool(verdict.get("ga_ready"))
    decision = "GA_SIGNED" if ga_ready else "RELEASE_CANDIDATE_BLOCKED"

    lines = [
        "# AIQE V1.6.2 Hardening Final Acceptance",
        "",
        "> 本文件由 `python scripts/aiqe/build_v162_final_acceptance.py --write` 生成。",
        "> Gate / 产品 TC / GA 状态取自机器判定；FIX disposition 取自人工台账并与证据路径交叉引用。",
        "",
        f"- release_candidate_sha: `{verdict.get('commit_sha') or '<unknown>'}`",
        f"- baseline_release_commit: `{verdict.get('baseline_release_commit') or '<unknown>'}`",
        "- baseline_version: `v1.6.2-hardening`",
        f"- environment: `{product.get('environment') or '<unknown>'}`",
        f"- tested_commit_sha: `{product.get('commit_sha') or '<unknown>'}`",
        "",
        "## Gate Summary",
        "",
        "| Gate | Status | Evidence | Acceptance |",
        "|---|---|---|---|",
    ]
    for key in ("A", "B", "C", "D", "E", "F", "G"):
        gate = gates.get(key) or {}
        lines.append(
            f"| {key} | **{gate.get('status', 'MISSING')}** | {gate.get('evidence', '—')} | "
            f"{gate.get('acceptance', '—')} |"
        )

    lines.extend(
        [
            "",
            "## Product TC Summary",
            "",
            "| TC ID | Runner | Run ID | Assertions | Artifacts | Status |",
            "|---|---|---|---|---|---|",
        ]
    )
    for index in range(1, 11):
        tc_id = f"TC-AIQE-{index:03d}"
        item = product_tests.get(tc_id) or {}
        execution = item.get("execution") or {}
        runner = item.get("runner") or {}
        lines.append(
            f"| {tc_id} | {runner.get('name') or runner.get('type') or '—'} | "
            f"{execution.get('run_id') or item.get('run_id') or '—'} | "
            f"{len(item.get('assertions') or [])} | {len(item.get('artifacts') or [])} | "
            f"**{item.get('status', 'MISSING')}** |"
        )

    lines.extend(
        [
            "",
            "## FIX Disposition",
            "",
            "| FIX ID | Status | Evidence | Reason / Blocker |",
            "|---|---|---|---|",
        ]
    )
    for fix_id in FIX_IDS:
        item = items.get(fix_id) or {}
        evidence = "<br>".join(f"`{path}`" for path in item.get("evidence") or []) or "—"
        reason = str(item.get("reason") or "—").replace("|", "/")
        lines.append(
            f"| {fix_id} | **{str(item.get('status') or 'MISSING')}** | {evidence} | {reason} |"
        )

    lines.extend(
        [
            "",
            "## Known Gaps",
            "",
        ]
    )
    gaps = disposition.get("known_gaps") or []
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- 未声明")
    lines.extend(
        [
            "",
            f"- 是否影响 GA：**{'否' if ga_ready else '是'}**",
            "",
            "## Final Decision",
            "",
            f"- [{'x' if decision == 'GA_SIGNED' else ' '}] GA_SIGNED",
            f"- [{'x' if decision == 'RELEASE_CANDIDATE_BLOCKED' else ' '}] RELEASE_CANDIDATE_BLOCKED",
            "- [ ] CONTROLLED_RELEASE_WITH_WAIVERS",
            "",
            f"- decision_reason: {disposition.get('decision_reason') or '机器 Gate 未全部 PASS'}",
            f"- approver_github_login: {disposition.get('approver_github_login') or '<pending>'}",
            f"- github_review_id: {disposition.get('github_review_id') or '<pending>'}",
            f"- approved_commit_sha: {disposition.get('approved_commit_sha') or '<pending>'}",
            "",
        ]
    )
    return "\n".join(lines), {
        "errors": errors,
        "decision": decision,
        "ga_ready": ga_ready,
        "fixes": items,
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="V1.6.2 final acceptance report")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--disposition", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    disposition = Path(args.disposition) if args.disposition else root / "docs/aiqe/v1.6/governance/v162-fix-disposition.yaml"
    text, meta = build_report(root, disposition_path=disposition)
    if args.write:
        output = Path(args.output) if args.output else root / "docs/aiqe/v1.6/V1.6.2-Hardening-Final-Acceptance.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
        print(json.dumps({"written": str(output), "decision": meta["decision"], "errors": meta["errors"]}, ensure_ascii=False))
    else:
        print(text)
    for error in meta["errors"]:
        print(f"::error::[final-acceptance] {error}", file=sys.stderr)
    return 0 if not meta["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
