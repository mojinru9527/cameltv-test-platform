"""V1.6 发布判定（单一路径）：从机器可校验证据计算 Gate A–G 与 GA 状态。

设计原则
--------
1. **不读散文**：判定只读结构化证据文件，不解析“已完成/已通过”等叙述文本。
2. **两维判定**：每个 Gate 同时记录 ``evidence``（工程证据是否齐备）与
   ``acceptance``（是否有非原作者独立验收）；只有两者都成立才是 ``PASS``。
3. **缺证据 = NOT_PROVEN**：缺 artifact、缺独立验收、缺 CI Run 一律 NOT_PROVEN，
   不允许用“文档写了”替代。
4. **单一出口**：``V1.6-GA-Release-Report.md`` 等文档的 Gate / TC 数字必须与
   ``release-verdict.json`` 一致；``check_release_audit.py`` 会做交叉校验。

用法
----
    python scripts/aiqe/release_verdict.py --write                        # 写 JSON
    python scripts/aiqe/release_verdict.py --write --emit-markdown out.md
    python scripts/aiqe/release_verdict.py --require-ga                   # 发布门禁
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(SCRIPT_DIR))
from acceptance_records import apply_records, load_records  # noqa: E402

DOCS = ROOT / "docs/aiqe/v1.6"
MATRIX = DOCS / "traceability/requirements.yaml"
VERDICT_JSON = DOCS / "release-verdict.json"
TRACEABILITY_SNAPSHOT = DOCS / "traceability/matrix-snapshot.json"
PLATFORM_RESULTS = DOCS / "e2e/platform-results.json"
RUNTIME_EVIDENCE_INDEX = DOCS / "evidence/evidence-index.json"
BRANCH_PROTECTION = DOCS / "governance/branch-protection.json"
PRODUCTION_EVIDENCE = DOCS / "governance/production-evidence.json"

PASS = "PASS"
FAIL = "FAIL"
NOT_PROVEN = "NOT_PROVEN"
REVIEWED = "REVIEWED"
PENDING = "PENDING"

GATE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "A": (),
    "B": ("V16-001", "V16-002", "V16-003", "V16-004"),
    "C": ("V16-005", "V16-006", "V16-007", "V16-008", "V16-009"),
    "D": ("V16-010", "V16-011", "V16-012", "V16-013", "V16-014", "V16-019"),
    "E": (),
    "F": (),
    "G": ("V16-025",),
}

GATE_TITLES = {
    "A": "代码与构建",
    "B": "安全边界",
    "C": "执行可靠性",
    "D": "Agent / Learning",
    "E": "Driver / E2E",
    "F": "生产运行",
    "G": "工程治理",
}


@dataclass
class Gate:
    key: str
    title: str
    evidence: str = NOT_PROVEN
    acceptance: str = PENDING
    reasons: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.evidence == FAIL:
            return FAIL
        if self.evidence == PASS and self.acceptance == REVIEWED:
            return PASS
        return NOT_PROVEN

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.key,
            "title": self.title,
            "status": self.status,
            "evidence": self.evidence,
            "acceptance": self.acceptance,
            "reasons": self.reasons,
            "artifacts": self.artifacts,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:  # pragma: no cover - 非 git 环境
        return "unknown"


def _entries_by_issue(matrix: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in matrix.get("requirements") or []:
        grouped.setdefault(str(entry.get("issue")), []).append(entry)
    return grouped


def _status_of(entries: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """一组需求的最小状态：任一 FAIL/BLOCKED 之外，全部 VERIFIED 才算 PASS。"""
    statuses = {str(entry.get("status") or "").upper() for entry in entries}
    ids = [str(entry.get("id")) for entry in entries]
    if not entries:
        return NOT_PROVEN, ["缺少需求条目"]
    if "BLOCKED" in statuses:
        blocked = [i for i in ids if _entry_status(entries, i) == "BLOCKED"]
        return FAIL, [f"BLOCKED: {', '.join(blocked)}"]
    if statuses <= {"VERIFIED", "ACCEPTED"}:
        return PASS, []
    degraded = [
        str(entry.get("id"))
        for entry in entries
        if str(entry.get("status") or "").upper() not in {"VERIFIED", "ACCEPTED"}
    ]
    return NOT_PROVEN, [f"未达 VERIFIED: {', '.join(degraded)}"]


def _entry_status(entries: list[dict[str, Any]], entry_id: str) -> str:
    for entry in entries:
        if str(entry.get("id")) == entry_id:
            return str(entry.get("status") or "").upper()
    return ""


def _acceptance_of(entries: list[dict[str, Any]]) -> tuple[str, list[str]]:
    pending = [
        str(entry.get("id"))
        for entry in entries
        if str((entry.get("acceptance") or {}).get("status") or "").upper() != "REVIEWED"
    ]
    if pending:
        return PENDING, [f"独立验收未完成: {', '.join(pending)}"]
    return REVIEWED, []


def _traceability_valid() -> tuple[bool, list[str]]:
    proc = subprocess.run(
        [
            "python",
            str(ROOT / "scripts/aiqe/check_traceability.py"),
            "--strict-warnings",
            "--check-baseline",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, []
    messages = [
        line.replace("::error::[traceability] ", "")
        for line in (proc.stdout or "").splitlines()
        if line.startswith("::error::")
    ]
    return False, messages or [f"check_traceability 退出码 {proc.returncode}"]


def _migration_head(matrix: dict[str, Any]) -> str:
    return str((matrix.get("baseline") or {}).get("migration_head") or "")


def _platform_results() -> dict[str, Any] | None:
    return _load_json(PLATFORM_RESULTS)


def _runtime_index() -> dict[str, Any] | None:
    return _load_json(RUNTIME_EVIDENCE_INDEX)


def _branch_protection() -> dict[str, Any] | None:
    return _load_json(BRANCH_PROTECTION)


def _production_evidence() -> dict[str, Any] | None:
    return _load_json(PRODUCTION_EVIDENCE)


def build_verdict() -> dict[str, Any]:
    matrix = _load_yaml(MATRIX)
    raw_entries = list(matrix.get("requirements") or [])
    acceptance_report = load_records(entries=raw_entries)
    entries = apply_records(raw_entries, acceptance_report)
    matrix = {**matrix, "requirements": entries}
    grouped = _entries_by_issue(matrix)
    gates: dict[str, Gate] = {}

    traceability_ok, traceability_reasons = _traceability_valid()
    expected_head = _migration_head(matrix)

    # ---------------- Gate A：代码与构建 ----------------
    gate_a = Gate("A", GATE_TITLES["A"])
    # Gate A 是机器可校验项（矩阵 strict + 迁移单头），不依赖人工验收。
    gate_a.acceptance = REVIEWED
    if traceability_ok:
        gate_a.evidence = PASS
        gate_a.reasons.append(
            f"追踪矩阵 strict 校验通过（{len(entries)} 条），migration head={expected_head}"
        )
    else:
        gate_a.evidence = FAIL
        gate_a.reasons.extend(traceability_reasons[:5])
    gates["A"] = gate_a

    def requirement_gate(key: str) -> Gate:
        gate = Gate(key, GATE_TITLES[key])
        issues = GATE_REQUIREMENTS[key]
        collected: list[dict[str, Any]] = []
        for issue in issues:
            collected.extend(grouped.get(issue, []))
        evidence_status, evidence_reasons = _status_of(collected)
        acceptance_status, acceptance_reasons = _acceptance_of(collected)
        gate.evidence = evidence_status
        gate.acceptance = acceptance_status
        gate.reasons.extend(evidence_reasons)
        gate.reasons.extend(acceptance_reasons)
        return gate

    for key in ("B", "C", "D"):
        gates[key] = requirement_gate(key)

    # ---------------- Gate E：真实 E2E ----------------
    gate_e = Gate("E", GATE_TITLES["E"])
    product_tcs = [entry for entry in entries if str(entry.get("id", "")).startswith("TC-AIQE-")]
    product_pass = [
        str(entry.get("id"))
        for entry in product_tcs
        if str(((entry.get("e2e") or {}).get("product") or {}).get("status") or "").upper() == PASS
    ]
    platform = _platform_results()
    runtime_index = _runtime_index()
    if len(product_pass) == 10:
        gate_e.evidence = PASS
    else:
        gate_e.evidence = NOT_PROVEN
        gate_e.reasons.append(
            f"产品级 TC PASS {len(product_pass)}/10；其余仅现场记录或未执行"
        )
    if platform is None:
        gate_e.reasons.append("缺少 docs/aiqe/v1.6/e2e/platform-results.json（平台链路机器结果）")
    else:
        gate_e.artifacts.append(str(PLATFORM_RESULTS.relative_to(ROOT)))
        passed = sum(1 for item in platform.get("tests") or [] if str(item.get("status")) == PASS)
        gate_e.reasons.append(
            f"平台链路机器结果: {passed}/{len(platform.get('tests') or [])} PASS"
            f"（commit {str(platform.get('commit_sha') or '')[:12]}）"
        )
    if runtime_index is None:
        gate_e.reasons.append(
            "缺少 docs/aiqe/v1.6/evidence/evidence-index.json（build_evidence_index.py 产物）"
        )
    else:
        gate_e.artifacts.append(str(RUNTIME_EVIDENCE_INDEX.relative_to(ROOT)))
        summary = runtime_index.get("summary") or {}
        if not summary.get("ga_ready"):
            gate_e.reasons.append(
                f"运行证据索引未达 GA：{json.dumps(summary, ensure_ascii=False)}"
            )
    gate_e.acceptance = _acceptance_of(product_tcs)[0]
    if len(product_pass) == 10 and gate_e.acceptance != REVIEWED:
        gate_e.reasons.append("产品 TC 缺少非原作者独立验收")
    gates["E"] = gate_e

    # ---------------- Gate F：生产运行 ----------------
    gate_f = Gate("F", GATE_TITLES["F"])
    production = _production_evidence()
    if production is None:
        gate_f.evidence = NOT_PROVEN
        gate_f.reasons.append("缺少 docs/aiqe/v1.6/governance/production-evidence.json")
    else:
        gate_f.artifacts.append(str(PRODUCTION_EVIDENCE.relative_to(ROOT)))
        stages = production.get("stages") or {}
        not_proven = [
            name
            for name, item in stages.items()
            if str((item or {}).get("status") or "").upper() != PASS
        ]
        if not_proven:
            gate_f.evidence = NOT_PROVEN
            gate_f.reasons.append(f"生产阶段未证明: {', '.join(sorted(not_proven))}")
        elif stages:
            gate_f.evidence = PASS
        else:
            gate_f.evidence = NOT_PROVEN
            gate_f.reasons.append("production-evidence.json 没有 stage 记录")
        if not (production.get("independent_verification") or {}).get("reviewed_by"):
            gate_f.reasons.append("生产验收无独立验收签署")
        else:
            gate_f.acceptance = REVIEWED
    gates["F"] = gate_f

    # ---------------- Gate G：工程治理 ----------------
    gate_g = Gate("G", GATE_TITLES["G"])
    governance_requirements: list[dict[str, Any]] = []
    for issue in GATE_REQUIREMENTS["G"]:
        governance_requirements.extend(grouped.get(issue, []))
    evidence_status, evidence_reasons = _status_of(governance_requirements)
    gate_g.evidence = evidence_status
    gate_g.reasons.extend(evidence_reasons)
    protection = _branch_protection()
    if protection is None:
        gate_g.reasons.append("缺少 docs/aiqe/v1.6/governance/branch-protection.json")
    else:
        gate_g.artifacts.append(str(BRANCH_PROTECTION.relative_to(ROOT)))
        if not protection.get("verified"):
            gate_g.reasons.append(
                "GitHub Branch Protection / Ruleset 未验证："
                + str(protection.get("reason") or "未提供导出或 API 查询结果")
            )
            if gate_g.evidence == PASS:
                gate_g.evidence = NOT_PROVEN
    acceptance_status, acceptance_reasons = _acceptance_of(governance_requirements)
    gate_g.acceptance = acceptance_status
    gate_g.reasons.extend(acceptance_reasons)
    if acceptance_report.errors:
        gate_g.reasons.append(
            "acceptance 记录无效: " + "; ".join(acceptance_report.errors[:5])
        )
    gates["G"] = gate_g

    blocking = [
        f"Gate {gate.key}: {reason}"
        for gate in gates.values()
        if gate.status != PASS
        for reason in (gate.reasons or ["未证明"])
    ]
    ga_ready = all(gate.status == PASS for gate in gates.values())

    summary = {
        "requirements": len(entries),
        "verified": sum(1 for entry in entries if str(entry.get("status")).upper() == "VERIFIED"),
        "accepted": sum(
            1
            for entry in entries
            if str(entry.get("status")).upper() == "ACCEPTED"
            and str((entry.get("acceptance") or {}).get("status") or "").upper() == REVIEWED
        ),
        "partial": sum(1 for entry in entries if str(entry.get("status")).upper() == "PARTIAL"),
        "blocked": sum(1 for entry in entries if str(entry.get("status")).upper() == "BLOCKED"),
        "independent_reviews": sum(
            1
            for entry in entries
            if str((entry.get("acceptance") or {}).get("status") or "").upper() == REVIEWED
        ),
        "runtime_not_proven": sum(
            1
            for entry in entries
            if str(((entry.get("runtime_evidence") or {}).get("status") or "")).upper()
            == "NOT_PROVEN"
        ),
        "product_tc_pass": len(product_pass),
        "product_tc_total": len(product_tcs) or 10,
    }
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "release": matrix.get("release", "aiqe-v1.6"),
        "commit_sha": _git_sha(),
        "baseline_release_commit": str((matrix.get("baseline") or {}).get("release_commit") or ""),
        "migration_head": expected_head,
        "summary": summary,
        "gates": {key: gates[key].to_dict() for key in sorted(gates)},
        "ga_ready": ga_ready,
        "ga_status": "GA_SIGNED" if ga_ready else "GA_NOT_READY",
        "blocking": blocking,
        "evidence_files": {
            "branch_protection": (
                str(BRANCH_PROTECTION.relative_to(ROOT)) if protection is not None else None
            ),
            "production_evidence": (
                str(PRODUCTION_EVIDENCE.relative_to(ROOT)) if production is not None else None
            ),
            "platform_results": (
                str(PLATFORM_RESULTS.relative_to(ROOT)) if platform is not None else None
            ),
            "runtime_evidence_index": (
                str(RUNTIME_EVIDENCE_INDEX.relative_to(ROOT)) if runtime_index is not None else None
            ),
        },
        "traceability": {
            "strict_validation": traceability_ok,
            "errors": traceability_reasons,
            "snapshot": str(TRACEABILITY_SNAPSHOT.relative_to(ROOT)),
        },
    }


def _render_markdown(verdict: dict[str, Any]) -> str:
    lines = [
        "# V1.6 发布判定（机器生成）",
        "",
        "> 本文件由 `python scripts/aiqe/release_verdict.py --write --emit-markdown` 生成，**禁止手工编辑**。",
        "> 判定口径：每个 Gate 必须同时满足 `evidence=PASS` 与 `acceptance=REVIEWED` 才是 `PASS`；",
        "> 缺 artifact / 缺独立验收 / 缺 CI Run 一律 `NOT_PROVEN`。",
        "",
        f"- 基线 release commit：`{verdict['baseline_release_commit']}`",
        f"- migration head：`{verdict['migration_head']}`",
        f"- **GA 状态：`{verdict['ga_status']}`**",
        "",
        "## Gate 状态",
        "",
        "| Gate | 标题 | 状态 | 证据 | 独立验收 | 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for key in ("A", "B", "C", "D", "E", "F", "G"):
        gate = verdict["gates"][key]
        reasons = "<br>".join(str(reason).replace("|", "/") for reason in gate["reasons"]) or "—"
        lines.append(
            f"| {key} | {gate['title']} | **{gate['status']}** | {gate['evidence']} | "
            f"{gate['acceptance']} | {reasons} |"
        )
    summary = verdict["summary"]
    lines.extend(
        [
            "",
            "## 汇总",
            "",
            "| 指标 | 数值 |",
            "|---|---:|",
            f"| requirements | {summary['requirements']} |",
            f"| VERIFIED | {summary['verified']} |",
            f"| ACCEPTED（含独立验收） | {summary['accepted']} |",
            f"| PARTIAL | {summary['partial']} |",
            f"| BLOCKED | {summary['blocked']} |",
            f"| 独立验收条目 | {summary['independent_reviews']} |",
            f"| 运行时证据 NOT_PROVEN | {summary['runtime_not_proven']} |",
            f"| 产品级 TC PASS | {summary['product_tc_pass']}/{summary['product_tc_total']} |",
            "",
            "## 阻塞项",
            "",
        ]
    )
    if verdict["blocking"]:
        lines.extend(f"- {item}" for item in verdict["blocking"])
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def _render_e2e_doc(verdict: dict[str, Any]) -> str:
    matrix = _load_yaml(MATRIX)
    entries = {str(entry.get("id")): entry for entry in matrix.get("requirements") or []}
    platform = _platform_results() or {"tests": []}
    platform_by_id = {str(item.get("tc_id")): item for item in platform.get("tests") or []}
    lines = [
        "# V1.6 E2E 覆盖与阻塞清单（机器生成）",
        "",
        "> 本文件由 `python scripts/aiqe/release_verdict.py --emit-e2e-doc` 生成，**禁止手工编辑**。",
        "> 产品级 TC（`TC-AIQE-*`）与平台链路 TC（`TC-PLATFORM-*`）是两个命名空间：",
        "> 平台链路通过**不等于**产品 TC 通过；产品 TC 必须有真实业务环境 artifact。",
        "",
        "## 产品级 TC（V16-017 原验收口径）",
        "",
        "| TC | 标题 | 产品状态 | 平台映射 | 缺口 / 证据 |",
        "|---|---|---|---|---|",
    ]
    for index in range(1, 11):
        tc_id = f"TC-AIQE-{index:03d}"
        entry = entries.get(tc_id, {})
        e2e = entry.get("e2e") or {}
        product = e2e.get("product") or {}
        platform_refs = (e2e.get("platform") or {}).get("tc_ids") or []
        gaps = entry.get("gaps") or []
        status = str(product.get("status") or "NOT_PROVEN")
        evidence = product.get("evidence") or []
        note = "<br>".join(
            str(item.get("note") or item.get("ref") or "") for item in evidence if isinstance(item, dict)
        )
        detail = "<br>".join(str(gap) for gap in gaps) or note or "—"
        lines.append(
            f"| {tc_id} | {entry.get('title', '—')} | **{status}** | "
            f"{', '.join(platform_refs) or '—'} | {detail} |"
        )
    product_pass = sum(
        1
        for index in range(1, 11)
        if str(
            (
                (entries.get(f"TC-AIQE-{index:03d}", {}).get("e2e") or {}).get("product") or {}
            ).get("status")
            or ""
        ).upper()
        == PASS
    )
    lines.extend(
        [
            "",
            f"**产品级 TC PASS：{product_pass}/10。**",
            "",
            "## 平台链路 TC（本地确定性 SUT，不是产品验收）",
            "",
            "| TC | 状态 | Run ID | Job | NodeRun | Assertion | Artifact | 说明 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for tc_id in sorted(platform_by_id):
        item = platform_by_id[tc_id]
        lines.append(
            "| {tc} | **{status}** | {run} | {jobs} | {nodes} | {assertions} | {artifacts} | {note} |".format(
                tc=tc_id,
                status=item.get("status"),
                run=str(item.get("run_id") or "—")[:8],
                jobs=",".join(str(x) for x in item.get("job_ids") or []) or "—",
                nodes=",".join(str(x)[:8] for x in item.get("node_run_ids") or []) or "—",
                assertions=",".join(str(x)[:8] for x in item.get("assertion_ids") or []) or "—",
                artifacts=",".join(str(x)[:8] for x in item.get("artifact_refs") or []) or "—",
                note=item.get("blocked_reason") or "",
            )
        )
    lines.extend(
        [
            "",
            f"- 平台结果文件：`{PLATFORM_RESULTS.relative_to(ROOT)}`（环境 "
            f"`{platform.get('environment')}`，机器产物含 Run/Job/Assertion/Artifact ID）。",
            "- 平台链路 5 类负向/阻断场景按 BLOCKED/NOT_RUN 记录，不计入 PASS；"
            "它们不构成产品验收证据。",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIQE V1.6 发布判定")
    parser.add_argument("--write", action="store_true", help="写入 docs/aiqe/v1.6/release-verdict.json")
    parser.add_argument("--emit-markdown", default="")
    parser.add_argument("--emit-e2e-doc", default="")
    parser.add_argument("--require-ga", action="store_true", help="GA 未签署时非零退出")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    verdict = build_verdict()
    if args.write:
        VERDICT_JSON.write_text(
            json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    if args.emit_markdown:
        target = Path(args.emit_markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_markdown(verdict), encoding="utf-8", newline="\n")
    if args.emit_e2e_doc:
        target = Path(args.emit_e2e_doc)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_e2e_doc(verdict), encoding="utf-8", newline="\n")
    if args.json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "ga_status": verdict["ga_status"],
                    "gates": {key: gate["status"] for key, gate in verdict["gates"].items()},
                    "summary": verdict["summary"],
                    "blocking": verdict["blocking"][:8],
                },
                ensure_ascii=False,
            )
        )
    if args.require_ga and not verdict["ga_ready"]:
        for item in verdict["blocking"]:
            print(f"::error::[release-verdict] {item}")
        print("::error::[release-verdict] GA 未签署，禁止宣称 GA / 10-10 / PRODUCTION_DEPLOYED")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
