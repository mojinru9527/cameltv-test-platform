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
from statuses import FAIL, NOT_PROVEN, PASS  # noqa: E402
from validators.branch import validate_branch_protection  # noqa: E402
from validators.models import GateCheck, combine  # noqa: E402
from validators.platform import validate_platform_results  # noqa: E402
from validators.product_tc import validate_product_config, validate_product_results  # noqa: E402
from validators.production import validate_production_evidence  # noqa: E402
from validators.runtime_index import validate_runtime_index  # noqa: E402

DOCS = ROOT / "docs/aiqe/v1.6"
MATRIX = DOCS / "traceability/requirements.yaml"
VERDICT_JSON = DOCS / "release-verdict.json"
TRACEABILITY_SNAPSHOT = DOCS / "traceability/matrix-snapshot.json"
PLATFORM_RESULTS = DOCS / "e2e/platform-results.json"
PRODUCT_RESULTS = DOCS / "e2e/product-results.json"
PRODUCT_CONFIG = DOCS / "e2e/product-tc-config.yaml"
RUNTIME_EVIDENCE_INDEX = DOCS / "evidence/evidence-index.json"
PG_READONLY_EVIDENCE = DOCS / "evidence/pg-readonly-role.json"
BRANCH_PROTECTION = DOCS / "governance/branch-protection.json"
PRODUCTION_EVIDENCE = DOCS / "governance/production-evidence.json"

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
    notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.evidence != PASS:
            return self.evidence
        if self.acceptance == REVIEWED:
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
            "notes": self.notes,
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


def _git_sha(root: Path = ROOT) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
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


def _acceptance_of(
    entries: list[dict[str, Any]], valid_reviewed_ids: set[str] | None = None
) -> tuple[str, list[str]]:
    pending = []
    for entry in entries:
        entry_id = str(entry.get("id"))
        if valid_reviewed_ids is not None and entry_id not in valid_reviewed_ids:
            pending.append(entry_id)
            continue
        if str((entry.get("acceptance") or {}).get("status") or "").upper() != "REVIEWED":
            pending.append(entry_id)
    if pending:
        return PENDING, [f"独立验收未完成: {', '.join(pending)}"]
    return REVIEWED, []


def _traceability_valid(root: Path = ROOT) -> tuple[bool, list[str]]:
    proc = subprocess.run(
        [
            "python",
            str(root / "scripts/aiqe/check_traceability.py"),
            "--strict-warnings",
            "--check-baseline",
        ],
        cwd=root,
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


def _production_evidence(root: Path = ROOT) -> dict[str, Any] | None:
    return _load_json(root / "docs/aiqe/v1.6/governance/production-evidence.json")


def _expected_commit(explicit: str = "", root: Path = ROOT) -> str:
    import os

    return (
        explicit
        or os.environ.get("AIQE_EXPECTED_COMMIT")
        or os.environ.get("RELEASE_TARGET_SHA")
        or _git_sha(root)
    )


def evaluate_gate_e(
    entries: list[dict[str, Any]],
    *,
    root: Path = ROOT,
    expected_commit: str = "",
    expected_environment: str = "",
    allow_local: bool = False,
) -> tuple[GateCheck, list[str]]:
    """Gate E：逐条验证产品 TC 本次真实执行结果，而不是只看 10/10 数字。

    任何一项缺失（runner/execution/SHA/环境/断言/artifact/provenance）都会让
    Gate E 非 PASS。静态 10/10 JSON 不再能让 Gate E PASS。
    """
    docs = root / "docs/aiqe/v1.6"
    config = _load_yaml(docs / "e2e/product-tc-config.yaml")
    results = _load_json(docs / "e2e/product-results.json")
    runtime_index = _load_json(docs / "evidence/evidence-index.json")
    platform = _load_json(docs / "e2e/platform-results.json")
    commit = _expected_commit(expected_commit, root=root)
    environment = expected_environment or str(config.get("environment") or "")
    product_tcs = [entry for entry in entries if str(entry.get("id", "")).startswith("TC-AIQE-")]
    artifacts: list[str] = []

    config_check = validate_product_config(config, root=root)
    results_check = validate_product_results(
        results,
        config,
        expected_commit=commit,
        expected_environment=environment,
        root=root,
        require_verified=True,
        require_baseline=True,
    )
    runtime_check = validate_runtime_index(
        runtime_index,
        expected_commit=commit,
        expected_environment=expected_environment or None,
        allow_local=allow_local,
        require_platform_tcs=10,
    )
    platform_check = validate_platform_results(
        platform,
        expected_commit=commit,
        expected_environment=expected_environment,
        allow_local=allow_local,
        require_tcs=10,
    )
    gate = combine(config_check, results_check, runtime_check, platform_check)
    for check in (config_check, results_check, runtime_check, platform_check):
        for ref in check.evidence_refs:
            if ref not in artifacts:
                artifacts.append(ref)

    # 矩阵声明与执行结果必须一致；矩阵 PASS 但本次未执行 = 冲突。
    matrix_pass = [
        str(entry.get("id"))
        for entry in product_tcs
        if str(((entry.get("e2e") or {}).get("product") or {}).get("status") or "").upper()
        == PASS
    ]
    result_pass = [
        str(item.get("tc_id"))
        for item in (results or {}).get("tests") or []
        if isinstance(item, dict) and str(item.get("status") or "").upper() == PASS
    ]
    if len(matrix_pass) != len(result_pass):
        gate.add(
            f"矩阵产品 PASS {len(matrix_pass)} 与本次执行 PASS {len(result_pass)} 不一致，禁止混用历史结论"
        )
    matrix_only = sorted(set(matrix_pass) - set(result_pass))
    if matrix_only:
        gate.add(f"矩阵声称 PASS 但本次执行未通过: {matrix_only}")
    if len(result_pass) != 10:
        gate.add(f"产品 TC 本次真实 PASS 仅 {len(result_pass)}/10，Gate E 不得 PASS")

    acceptance, acceptance_reasons = _acceptance_of(product_tcs)
    if acceptance != REVIEWED:
        gate.add("；".join(acceptance_reasons) or "产品 TC 缺少独立验收")
    if gate.status == PASS:
        gate.note("Gate E：10 条产品 TC 本次执行链、断言、artifact 与 SHA 全部语义验证通过")
    return gate, artifacts


def evaluate_gate_f(
    *,
    root: Path = ROOT,
    expected_commit: str = "",
    allow_waivers: bool = False,
) -> tuple[GateCheck, list[str]]:
    docs = root / "docs/aiqe/v1.6"
    production = _load_json(docs / "governance/production-evidence.json")
    commit = _expected_commit(expected_commit, root=root)
    check = validate_production_evidence(
        production,
        expected_commit=commit,
        root=root,
        allow_waivers=allow_waivers,
    )
    artifacts = ["docs/aiqe/v1.6/governance/production-evidence.json"] if production else []
    return check, artifacts


def build_verdict(root: Path = ROOT) -> dict[str, Any]:
    docs = root / "docs/aiqe/v1.6"
    matrix_path = docs / "traceability/requirements.yaml"
    pg_path = docs / "evidence/pg-readonly-role.json"
    branch_path = docs / "governance/branch-protection.json"
    production_path = docs / "governance/production-evidence.json"
    platform_path = docs / "e2e/platform-results.json"
    product_path = docs / "e2e/product-results.json"
    runtime_path = docs / "evidence/evidence-index.json"
    snapshot_path = docs / "traceability/matrix-snapshot.json"

    matrix = _load_yaml(matrix_path)
    raw_entries = list(matrix.get("requirements") or [])
    acceptance_report = load_records(
        records_dir=docs / "acceptance/records",
        role_matrix_path=docs / "governance/review-roles.yaml",
        entries=raw_entries,
        require_github_identity=True,
    )
    entries = apply_records(raw_entries, acceptance_report)
    reviewed_ids = {
        requirement_id
        for requirement_id, record in acceptance_report.records.items()
        if str(record.get("status") or "").upper() == REVIEWED
    }
    matrix = {**matrix, "requirements": entries}
    grouped = _entries_by_issue(matrix)
    gates: dict[str, Gate] = {}

    traceability_ok, traceability_reasons = _traceability_valid(root)
    expected_head = _migration_head(matrix)
    # 生成型文档必须与当前 CI checkout SHA 解耦：默认使用矩阵基线，release/tag 场景由
    # 环境变量 AIQE_EXPECTED_COMMIT 强制为实际发布 SHA。
    import os

    baseline_commit = str((matrix.get("baseline") or {}).get("release_commit") or "")
    expected_commit = os.environ.get("AIQE_EXPECTED_COMMIT") or baseline_commit

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
        acceptance_status, acceptance_reasons = _acceptance_of(collected, reviewed_ids)
        gate.evidence = evidence_status
        gate.acceptance = acceptance_status
        gate.reasons.extend(evidence_reasons)
        gate.reasons.extend(acceptance_reasons)
        return gate

    for key in ("B", "C", "D"):
        gates[key] = requirement_gate(key)

    # Gate B 补充：PostgreSQL 只读角色必须有真实 PG 证据（SQLite mode=ro 不算）。
    pg_evidence = _load_json(pg_path)
    if pg_evidence is None:
        gates["B"].reasons.append(
            "缺少 docs/aiqe/v1.6/evidence/pg-readonly-role.json（真实 PG 只读角色未验证）"
        )
    else:
        gates["B"].artifacts.append(pg_path.relative_to(root).as_posix())
        pg_status = str(pg_evidence.get("status") or "").upper()
        if pg_status == FAIL:
            gates["B"].evidence = FAIL
        elif pg_status != PASS:
            gates["B"].evidence = NOT_PROVEN
        if pg_status != PASS:
            gates["B"].reasons.append(
                "PostgreSQL 只读角色未验证: "
                + str(pg_evidence.get("reason") or pg_evidence.get("error") or pg_status)
            )

    # ---------------- Gate E：真实 E2E ----------------
    gate_e = Gate("E", GATE_TITLES["E"])
    product_tcs = [entry for entry in entries if str(entry.get("id", "")).startswith("TC-AIQE-")]
    product_pass = [
        str(entry.get("id"))
        for entry in product_tcs
        if str(((entry.get("e2e") or {}).get("product") or {}).get("status") or "").upper() == PASS
    ]
    gate_e_check, gate_e_artifacts = evaluate_gate_e(
        entries,
        root=root,
        expected_commit=expected_commit,
        expected_environment=str(
            (_load_yaml(docs / "e2e/product-tc-config.yaml") or {}).get("environment") or ""
        ),
    )
    gate_e.evidence = gate_e_check.status
    gate_e.reasons.extend(gate_e_check.reasons)
    gate_e.notes.extend(gate_e_check.notes)
    gate_e.artifacts.extend(gate_e_artifacts)
    gate_e.acceptance = _acceptance_of(product_tcs, reviewed_ids)[0]
    gates["E"] = gate_e

    # ---------------- Gate F：生产运行 ----------------
    gate_f = Gate("F", GATE_TITLES["F"])
    gate_f_check, gate_f_artifacts = evaluate_gate_f(root=root, expected_commit=expected_commit)
    gate_f.evidence = gate_f_check.status
    gate_f.reasons.extend(gate_f_check.reasons)
    gate_f.notes.extend(gate_f_check.notes)
    gate_f.artifacts.extend(gate_f_artifacts)
    production = _load_json(production_path)
    independent = (production or {}).get("independent_verification") or {}
    if all(str(independent.get(field) or "").strip() for field in ("reviewed_by", "review_id", "reviewed_commit_sha")):
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
    protection = _load_json(branch_path)
    if protection is None:
        gate_g.reasons.append("缺少 docs/aiqe/v1.6/governance/branch-protection.json")
        gate_g.evidence = NOT_PROVEN
    else:
        gate_g.artifacts.append(branch_path.relative_to(root).as_posix())
        branch_check = validate_branch_protection(protection)
        if branch_check.status != PASS:
            gate_g.evidence = combine(
                GateCheck(gate_g.evidence, list(gate_g.reasons)), branch_check
            ).status
        gate_g.reasons.extend(branch_check.reasons)
        gate_g.notes.extend(branch_check.notes)
    acceptance_status, acceptance_reasons = _acceptance_of(governance_requirements, reviewed_ids)
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
        "commit_sha": _git_sha(root),
        "baseline_release_commit": str((matrix.get("baseline") or {}).get("release_commit") or ""),
        "migration_head": expected_head,
        "summary": summary,
        "gates": {key: gates[key].to_dict() for key in sorted(gates)},
        "ga_ready": ga_ready,
        "ga_status": "GA_SIGNED" if ga_ready else "GA_NOT_READY",
        "release_status": "GA_SIGNED" if ga_ready else "RELEASE_CANDIDATE_BLOCKED",
        "blocking": blocking,
        "evidence_files": {
            "branch_protection": (
                branch_path.relative_to(root).as_posix() if protection is not None else None
            ),
            "production_evidence": (
                production_path.relative_to(root).as_posix() if production is not None else None
            ),
            "platform_results": (
                platform_path.relative_to(root).as_posix() if platform_path.exists() else None
            ),
            "product_results": (
                product_path.relative_to(root).as_posix() if product_path.exists() else None
            ),
            "runtime_evidence_index": (
                runtime_path.relative_to(root).as_posix() if runtime_path.exists() else None
            ),
            "pg_readonly_role": (
                pg_path.relative_to(root).as_posix() if pg_evidence is not None else None
            ),
        },
        "traceability": {
            "strict_validation": traceability_ok,
            "errors": traceability_reasons,
            "snapshot": snapshot_path.relative_to(root).as_posix(),
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
        reasons = "<br>".join(
            str(reason).replace("|", "/")
            for reason in (gate["reasons"] or gate.get("notes") or [])
        ) or "—"
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
            f"- 平台结果文件：`{PLATFORM_RESULTS.relative_to(ROOT).as_posix()}`（环境 "
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
    parser.add_argument("--root", default=str(ROOT), help="仓库根目录（测试 fixture 可覆盖）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    verdict = build_verdict(root)
    if args.write:
        target = root / "docs/aiqe/v1.6/release-verdict.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
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
