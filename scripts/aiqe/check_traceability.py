"""V16-025：AIQE V1.6 需求—代码—正式入口—测试—证据 追踪门禁。

用法
----
    # 全量校验（CI / 本地）
    python scripts/aiqe/check_traceability.py

    # PR 模式：校验 PR 描述里的 Issue、变更文件是否被追踪矩阵覆盖
    python scripts/aiqe/check_traceability.py \
        --issue V16-001 --pr-body pr-body.md --changed-files changed.txt

    # 生成机器可读证据索引
    python scripts/aiqe/check_traceability.py --emit-evidence-index evidence-index.json

退出码
------
0  通过
1  存在 error（必须修复）
2  仅存在 warning 且使用了 --strict-warnings

设计边界
--------
本脚本只校验**追踪关系**（文件/测试是否存在、状态是否合法、证据是否声明），
不通过文件名/类名猜测代码是否真的实现了需求。真实实现证明仍由
Runtime E2E / 独立验收负责。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # pragma: no cover - CI 会显式安装
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "docs/aiqe/v1.6/traceability/requirements.yaml"

ISSUES: tuple[str, ...] = tuple(f"V16-{index:03d}" for index in range(1, 26))
TEST_CASES: tuple[str, ...] = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))
REQUIRED_ISSUES = ISSUES + TEST_CASES

P0_P1 = {"P0", "P1"}
STATUS_VALUES = {
    "NOT_STARTED",
    "PARTIAL",
    "IMPLEMENTED",
    "VERIFIED",
    "ACCEPTED",
    "BLOCKED",
}
PASSING_STATUS = {"VERIFIED", "ACCEPTED"}
REQUIRED_FIELDS = (
    "id",
    "issue",
    "priority",
    "title",
    "requirement",
    "invariant",
    "status",
    "owner",
)
EVIDENCE_RE = re.compile(r"^(commit:[0-9a-f]{7,40}|ci:[^\s]+|run:[^\s]+|pytest:[^\s]+|manual:[^\s]+)$")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class TestRef:
    file: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.file}::{self.name}"


def _load_matrix(path: Path, report: Report) -> dict[str, Any]:
    if not path.exists():
        report.error(f"追踪矩阵不存在: {path.relative_to(REPO_ROOT)}")
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:  # pragma: no cover - 语法错误
            report.error(f"追踪矩阵 YAML 解析失败: {exc}")
            return {}
    else:  # pragma: no cover - 无 PyYAML 时退化为 JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            report.error(f"没有 PyYAML 且矩阵不是合法 JSON: {exc}")
            return {}
    if not isinstance(data, dict):
        report.error("追踪矩阵根节点必须是对象")
        return {}
    return data


def _parse_test_ref(raw: str, report: Report, *, issue_id: str) -> TestRef | None:
    text = str(raw or "").strip()
    if "::" not in text:
        report.error(f"{issue_id}: 测试引用必须写成 path::test_name: {text or '<empty>'}")
        return None
    file_part, name = text.split("::", 1)
    file_part = file_part.strip()
    name = name.strip()
    if not file_part.endswith(".py"):
        report.error(f"{issue_id}: 测试文件必须是 .py: {file_part}")
        return None
    if not name or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        report.error(f"{issue_id}: 非法测试函数名: {name}")
        return None
    base = REPO_ROOT / "test-platform-v2/backend" / file_part
    candidates = [base, REPO_ROOT / file_part]
    resolved = next((candidate for candidate in candidates if candidate.exists()), None)
    if resolved is None:
        report.error(f"{issue_id}: 测试文件不存在: {file_part}")
        return None
    body = resolved.read_text(encoding="utf-8")
    if not re.search(rf"^def {re.escape(name)}\(", body, re.MULTILINE) and not re.search(
        rf"^class {re.escape(name)}\b", body, re.MULTILINE
    ):
        report.error(f"{issue_id}: 测试文件中找不到函数/类: {file_part}::{name}")
        return None
    return TestRef(file=file_part, name=name)


def _check_path(path_text: str, report: Report, *, issue_id: str) -> bool:
    raw = str(path_text or "").strip()
    if not raw:
        report.error(f"{issue_id}: code path 不能为空")
        return False
    if any(char in raw for char in "*?["):
        matches = list(REPO_ROOT.glob(raw))
        if not matches:
            report.error(f"{issue_id}: code glob 无匹配: {raw}")
            return False
        return True
    if not (REPO_ROOT / raw).exists():
        report.error(f"{issue_id}: code path 不存在: {raw}")
        return False
    return True


def _validate_requirement(
    entry: dict[str, Any], report: Report, seen_ids: set[str]
) -> dict[str, Any]:
    for field_name in REQUIRED_FIELDS:
        if not str(entry.get(field_name) or "").strip():
            report.error(f"需求条目缺少字段 {field_name}: {entry.get('id') or entry}")
    req_id = str(entry.get("id") or "").strip()
    issue_id = str(entry.get("issue") or "").strip()
    if not req_id or not issue_id:
        return {}
    if req_id in seen_ids:
        report.error(f"重复的需求 ID: {req_id}")
    seen_ids.add(req_id)
    if issue_id not in REQUIRED_ISSUES:
        report.error(f"{req_id}: 未知 issue {issue_id}（只允许 V16-001..025 / TC-AIQE-001..010）")
    status = str(entry.get("status") or "").strip().upper()
    if status not in STATUS_VALUES:
        report.error(f"{req_id}: 非法 status {status!r}（允许 {sorted(STATUS_VALUES)}）")
    priority = str(entry.get("priority") or "").strip().upper()
    if priority not in {"P0", "P1", "P2"}:
        report.error(f"{req_id}: 非法 priority {priority!r}")

    code_entries = entry.get("code") or []
    if not isinstance(code_entries, list):
        report.error(f"{req_id}: code 必须是数组")
        code_entries = []
    for item in code_entries:
        path_text = item.get("path") if isinstance(item, dict) else item
        _check_path(str(path_text or ""), report, issue_id=req_id)

    entries = entry.get("production_entry") or []
    if not isinstance(entries, list):
        report.error(f"{req_id}: production_entry 必须是数组")
        entries = []

    tests = entry.get("tests") or {}
    if not isinstance(tests, dict):
        report.error(f"{req_id}: tests 必须是对象（success/negative/boundary/concurrency）")
        tests = {}
    parsed_tests: dict[str, list[TestRef]] = {}
    for kind in ("success", "negative", "boundary", "concurrency"):
        refs = tests.get(kind) or []
        if not isinstance(refs, list):
            report.error(f"{req_id}: tests.{kind} 必须是数组")
            refs = []
        parsed_tests[kind] = [
            ref for ref in (_parse_test_ref(item, report, issue_id=req_id) for item in refs) if ref
        ]

    evidence = entry.get("evidence") or []
    if not isinstance(evidence, list):
        report.error(f"{req_id}: evidence 必须是数组")
        evidence = []
    for item in evidence:
        if not EVIDENCE_RE.match(str(item or "").strip()):
            report.warn(f"{req_id}: evidence 格式建议为 commit:/ci:/run:/pytest:/manual: → {item!r}")

    layers = entry.get("layers") or []
    if not isinstance(layers, list):
        report.error(f"{req_id}: layers 必须是数组")
        layers = []
    for layer in layers:
        if str(layer) not in {"L1", "L2", "L3", "L4"}:
            report.error(f"{req_id}: 非法测试层级 {layer!r}")

    reviewer = str(entry.get("reviewer") or "").strip()
    owner = str(entry.get("owner") or "").strip()
    gaps = entry.get("gaps") or []
    if not isinstance(gaps, list):
        report.error(f"{req_id}: gaps 必须是数组")
        gaps = []

    if status in {"VERIFIED", "ACCEPTED"}:
        if not parsed_tests.get("success"):
            report.error(f"{req_id}: {status} 需要至少一条成功路径测试")
        if priority in P0_P1 and not parsed_tests.get("negative"):
            report.error(f"{req_id}: {status} 的 P0/P1 需求需要至少一条拒绝/失败路径测试")
        if not set(str(layer) for layer in layers) & {"L2", "L3", "L4"}:
            report.error(f"{req_id}: {status} 需要 L2/L3/L4 之一（禁止只靠 L1 单元测试）")
        if not evidence:
            report.error(f"{req_id}: {status} 需要证据条目")
        if not entries:
            report.error(f"{req_id}: {status} 需要声明正式入口")
    if status == "ACCEPTED":
        if reviewer.lower() in {"", "pending", "tbd", "n/a"} or reviewer == owner:
            report.error(f"{req_id}: ACCEPTED 需要非原作者的独立 reviewer（当前 {reviewer!r}）")
    if status == "IMPLEMENTED" and not code_entries:
        report.error(f"{req_id}: IMPLEMENTED 需要代码映射")
    if status == "BLOCKED":
        for required in ("blocked_reason", "owner", "review_by"):
            if not str(entry.get(required) or "").strip():
                report.error(f"{req_id}: BLOCKED 必须填写 {required}")
    if status in {"NOT_STARTED", "PARTIAL"} and priority == "P0":
        report.warn(f"{req_id}: P0 需求仍为 {status}")

    entry["_parsed_tests"] = parsed_tests
    entry["_status"] = status
    entry["_priority"] = priority
    return entry


def _coverage_checks(entries: list[dict[str, Any]], report: Report) -> dict[str, list[dict[str, Any]]]:
    by_issue: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_issue.setdefault(str(entry.get("issue")), []).append(entry)
    for issue_id in REQUIRED_ISSUES:
        if issue_id not in by_issue:
            report.error(f"追踪矩阵缺少 issue 记录: {issue_id}")
    for issue_id, items in by_issue.items():
        if issue_id.startswith("TC-") and not any(
            item.get("_parsed_tests", {}).get("success") for item in items
        ):
            report.warn(f"{issue_id}: 尚无成功路径测试（TC 必须独立 fixture 与业务断言）")
    return by_issue


def _pr_mode(
    entries: list[dict[str, Any]],
    args: argparse.Namespace,
    report: Report,
) -> None:
    issue_ids = [str(item).strip() for item in (args.issue or []) if str(item).strip()]
    if not issue_ids:
        report.error("PR 模式需要至少一个 --issue")
        return
    for issue_id in issue_ids:
        if issue_id not in REQUIRED_ISSUES:
            report.error(f"--issue 非法: {issue_id}")
    if args.pr_body:
        body_path = Path(args.pr_body)
        if not body_path.exists():
            report.error(f"PR 描述文件不存在: {body_path}")
        else:
            body = body_path.read_text(encoding="utf-8")
            for issue_id in issue_ids:
                if issue_id not in body:
                    report.error(f"PR 描述未声明要求追踪的 issue: {issue_id}")
            if "Requirement ID" not in body and "需求 ID" not in body:
                report.error("PR 描述缺少 Requirement ID 字段")
            if "正式入口" not in body and "Production Entry" not in body:
                report.error("PR 描述缺少正式入口（Production Entry）说明")
            if "Mock" not in body:
                report.error("PR 描述缺少 Mock 边界说明")
            if "Reviewer" not in body and "验收人" not in body:
                report.error("PR 描述缺少 Reviewer/验收人")
    if args.changed_files:
        changed_path = Path(args.changed_files)
        if not changed_path.exists():
            report.error(f"变更文件清单不存在: {changed_path}")
            return
        changed = [
            line.strip()
            for line in changed_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        mapped: set[str] = set()
        for entry in entries:
            if str(entry.get("issue")) not in issue_ids:
                continue
            for item in entry.get("code") or []:
                path_text = str(item.get("path") if isinstance(item, dict) else item or "").strip()
                if path_text:
                    mapped.add(path_text)
        relevant_tests = {
            "test-platform-v2/backend/tests",
            "docs/aiqe/v1.6",
            "scripts/aiqe",
            ".github",
            "test-platform-v2/backend/alembic/versions",
            "scripts/qa",
        }
        for path in changed:
            if path in mapped:
                continue
            if any(path.startswith(prefix) for prefix in relevant_tests):
                continue
            report.warn(f"变更文件未被追踪矩阵 code 映射覆盖: {path}")


def _git_sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except Exception:  # pragma: no cover - 非 git 环境
        return "unknown"


def _emit_evidence_index(
    matrix: dict[str, Any], entries: list[dict[str, Any]], target: Path, args: argparse.Namespace
) -> None:
    baseline = matrix.get("baseline") or {}
    payload = {
        "schema_version": "1.0",
        "release": matrix.get("release", "aiqe-v1.6"),
        "commit_sha": args.commit_sha or _git_sha(),
        "ci_run": args.ci_run or "",
        "environment": args.environment or "local",
        "baseline": {
            "main_sha": baseline.get("main_sha"),
            "audit_snapshot_sha": baseline.get("audit_snapshot_sha"),
            "migration_head": baseline.get("migration_head"),
        },
        "summary": {
            "requirements": len(entries),
            "verified": sum(1 for item in entries if item.get("_status") in PASSING_STATUS),
            "blocked": sum(1 for item in entries if item.get("_status") == "BLOCKED"),
            "not_started": sum(1 for item in entries if item.get("_status") == "NOT_STARTED"),
        },
        "requirements": [
            {
                "id": item.get("id"),
                "issue": item.get("issue"),
                "priority": item.get("_priority"),
                "status": item.get("_status"),
                "owner": item.get("owner"),
                "reviewer": item.get("reviewer"),
                "production_entry": item.get("production_entry") or [],
                "tests": {
                    kind: [ref.label for ref in refs]
                    for kind, refs in (item.get("_parsed_tests") or {}).items()
                },
                "layers": item.get("layers") or [],
                "evidence": item.get("evidence") or [],
                "gaps": item.get("gaps") or [],
            }
            for item in entries
        ],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _emit_markdown(
    matrix: dict[str, Any], entries: list[dict[str, Any]], target: Path
) -> None:
    """从 YAML 生成人类可读矩阵；Markdown 不允许手工编辑（避免与 YAML 漂移）。"""
    baseline = matrix.get("baseline") or {}
    order = {issue: index for index, issue in enumerate(REQUIRED_ISSUES)}
    ordered = sorted(entries, key=lambda item: (order.get(str(item.get("issue")), 999), str(item.get("id"))))
    status_counts: dict[str, int] = {}
    for item in ordered:
        status = str(item.get("_status"))
        status_counts[status] = status_counts.get(status, 0) + 1
    lines: list[str] = []
    lines.append("# CamelTv AIQE V1.6 需求—代码—正式入口—测试—证据矩阵")
    lines.append("")
    lines.append("> 本文件由 `python scripts/aiqe/check_traceability.py --emit-markdown` 从")
    lines.append("> `docs/aiqe/v1.6/traceability/requirements.yaml` 生成，**禁止手工编辑**。")
    lines.append("> 状态语义：`NOT_STARTED` / `PARTIAL` / `IMPLEMENTED` 不计入通过率；")
    lines.append("> 只有 `VERIFIED`（正式入口 L2/L3 测试通过）与 `ACCEPTED`（非原作者复核）计入。")
    lines.append("")
    lines.append("## 基线")
    lines.append("")
    lines.append(f"- release: `{matrix.get('release', 'aiqe-v1.6')}`")
    lines.append(f"- main SHA: `{baseline.get('main_sha', '')}`")
    lines.append(f"- V1.5 审计快照: `{baseline.get('audit_snapshot_sha', '')}`")
    lines.append(f"- 迁移 head: `{baseline.get('migration_head', '')}`")
    lines.append("")
    lines.append("## 状态汇总")
    lines.append("")
    lines.append("| 状态 | 数量 |")
    lines.append("|---|---:|")
    for status in ("VERIFIED", "ACCEPTED", "IMPLEMENTED", "PARTIAL", "NOT_STARTED", "BLOCKED"):
        lines.append(f"| {status} | {status_counts.get(status, 0)} |")
    lines.append(f"| **合计** | **{len(ordered)}** |")
    lines.append("")
    lines.append("## 需求追踪")
    lines.append("")
    lines.append("| Requirement | Issue | 优先级 | 状态 | Owner | Reviewer | 正式入口 | 成功/拒绝测试 | 层级 | 证据 | 未决风险 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for item in ordered:
        tests = item.get("_parsed_tests") or {}
        success = tests.get("success") or []
        negative = tests.get("negative") or []
        test_cell = []
        if success:
            test_cell.append(f"✅ {len(success)}")
        if negative:
            test_cell.append(f"⛔ {len(negative)}")
        gaps = item.get("gaps") or []
        gap_text = "<br>".join(str(gap).replace("|", "/") for gap in gaps) if gaps else "—"
        lines.append(
            "| {id} | {issue} | {priority} | {status} | {owner} | {reviewer} | {entry} | {tests} | {layers} | {evidence} | {gaps} |".format(
                id=item.get("id"),
                issue=item.get("issue"),
                priority=item.get("_priority"),
                status=item.get("_status"),
                owner=item.get("owner"),
                reviewer=item.get("reviewer") or "pending",
                entry="<br>".join(str(x) for x in (item.get("production_entry") or [])),
                tests=" / ".join(test_cell) or "—",
                layers=", ".join(str(x) for x in (item.get("layers") or [])) or "—",
                evidence="<br>".join(str(x) for x in (item.get("evidence") or [])) or "—",
                gaps=gap_text,
            )
        )
    lines.append("")
    lines.append("## 需求正文与不变量")
    lines.append("")
    for item in ordered:
        lines.append(f"### {item.get('id')} — {item.get('title')}")
        lines.append("")
        lines.append(f"- Issue: `{item.get('issue')}` / 优先级 `{item.get('_priority')}` / 状态 `{item.get('_status')}`")
        lines.append(f"- 需求：{item.get('requirement')}")
        lines.append(f"- 不变量：{item.get('invariant')}")
        code = item.get("code") or []
        if code:
            rendered = []
            for entry in code:
                if isinstance(entry, dict):
                    symbol = f" `{entry.get('symbol')}`" if entry.get("symbol") else ""
                    change = f"（{entry.get('change')}）" if entry.get("change") else ""
                    rendered.append(f"`{entry.get('path')}`{symbol}{change}")
                else:
                    rendered.append(f"`{entry}`")
            lines.append(f"- 代码映射：{'；'.join(rendered)}")
        tests = item.get("_parsed_tests") or {}
        for kind, label in (
            ("success", "成功路径"),
            ("negative", "拒绝/失败路径"),
            ("boundary", "边界"),
            ("concurrency", "并发/重试"),
        ):
            refs = tests.get(kind) or []
            if refs:
                lines.append(f"- {label}：{'；'.join(f'`{ref.label}`' for ref in refs)}")
        if item.get("mock_boundary"):
            lines.append(f"- Mock 边界：{item.get('mock_boundary')}")
        if item.get("evidence"):
            lines.append(f"- 证据：{'；'.join(str(x) for x in item.get('evidence'))}")
        lines.append("")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIQE V1.6 追踪矩阵门禁")
    parser.add_argument("--matrix", default=str(MATRIX_PATH))
    parser.add_argument("--issue", action="append", default=[])
    parser.add_argument("--pr-body", default="")
    parser.add_argument("--changed-files", default="")
    parser.add_argument("--emit-evidence-index", default="")
    parser.add_argument("--emit-markdown", default="")
    parser.add_argument("--commit-sha", default="")
    parser.add_argument("--ci-run", default="")
    parser.add_argument("--environment", default="")
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument("--summary", default="")
    args = parser.parse_args(argv)

    report = Report()
    matrix = _load_matrix(Path(args.matrix), report)
    raw_entries = matrix.get("requirements") or []
    if not isinstance(raw_entries, list) or not raw_entries:
        report.error("追踪矩阵 requirements 不能为空")
        raw_entries = []

    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, dict):
            report.error(f"需求条目必须是对象: {raw!r}")
            continue
        validated = _validate_requirement(raw, report, seen_ids)
        if validated:
            entries.append(validated)

    _coverage_checks(entries, report)
    pr_mode = bool(args.issue or args.pr_body or args.changed_files)
    if pr_mode:
        _pr_mode(entries, args, report)

    if args.emit_evidence_index:
        _emit_evidence_index(matrix, entries, Path(args.emit_evidence_index), args)
    if args.emit_markdown:
        _emit_markdown(matrix, entries, Path(args.emit_markdown))

    summary = {
        "requirements": len(entries),
        "verified": sum(1 for item in entries if item.get("_status") in PASSING_STATUS),
        "blocked": sum(1 for item in entries if item.get("_status") == "BLOCKED"),
        "not_started": sum(1 for item in entries if item.get("_status") == "NOT_STARTED"),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    if args.summary:
        Path(args.summary).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    for warning in report.warnings:
        print(f"::warning::[traceability] {warning}")
    for error in report.errors:
        print(f"::error::[traceability] {error}")
    print(json.dumps(summary, ensure_ascii=False))
    if report.errors:
        return 1
    if args.strict_warnings and report.warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
