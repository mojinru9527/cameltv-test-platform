"""V16-025：AIQE V1.6 需求—代码—正式入口—测试—证据 追踪门禁（v2.0）。

v2.0 相对 v1.0 的变化
---------------------
1. **状态与验收分离**：``status`` 只表达交付/自动证据等级；独立验收必须写在
   ``acceptance.status``（``REVIEWED``/``WAIVED``），并要求非原作者 Reviewer 与
   仓库内 artifact。``VERIFIED`` 不再隐含“已独立验收”。
2. **证据类型化**：``commit:/ci:/run:/pytest:/script:/live:/manual:/human:/artifact:``
   各自有校验规则；未知类型或裸字符串直接报错（不再放行）。
3. **运行时证据分层**：出现 ``live:/manual:/human:/script:`` 的条目必须声明
   ``runtime_evidence``；``PROVEN`` 需要仓库内 artifact 与机器 ID，否则
   ``NOT_PROVEN``，且不得把该条目计为运行验收。
4. **TC 双命名空间**：``TC-AIQE-*`` 是产品级验收，必须声明 ``e2e.product`` 与
   ``e2e.platform``；平台链路记录用 ``TC-PLATFORM-*``，不得冒充产品 TC。
5. **基线唯一**：``--check-baseline`` 校验 release commit 与 Alembic 单头，禁止
   追踪矩阵里出现过期 SHA / migration head。

用法
----
    # 全量校验（CI / 本地）
    python scripts/aiqe/check_traceability.py --strict-warnings --check-baseline

    # PR 模式：校验 PR 描述字段、Issue 与变更文件追踪
    python scripts/aiqe/check_traceability.py \
        --issue V16-001 --pr-body pr-body.md --changed-files changed.txt --pr-author mojinru9527

    # 发布门禁（release tag / 发布 PR）：要求独立验收与运行时证据已完成
    python scripts/aiqe/check_traceability.py --release-gate

退出码
------
0  通过
1  存在 error（必须修复）
2  仅存在 warning 且使用了 --strict-warnings

设计边界
--------
本脚本只校验**追踪关系与证据形态**，不通过文件名/类名猜测实现是否正确；真实实现
证明仍由 Runtime E2E 产物（``build_evidence_index.py``）与独立验收负责。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

try:  # pragma: no cover - CI 会显式安装
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "docs/aiqe/v1.6/traceability/requirements.yaml"
BACKEND_ROOT = REPO_ROOT / "test-platform-v2/backend"
ALEMBIC_VERSIONS = BACKEND_ROOT / "alembic/versions"

ISSUES: tuple[str, ...] = tuple(f"V16-{index:03d}" for index in range(1, 26))
TEST_CASES: tuple[str, ...] = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))
REQUIRED_ISSUES = ISSUES + TEST_CASES
PRODUCT_TC_RE = re.compile(r"^TC-AIQE-\d{3}$")
PLATFORM_TC_RE = re.compile(r"^TC-PLATFORM-\d{3}$")

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
ACCEPTANCE_VALUES = {"NOT_REVIEWED", "REVIEWED", "WAIVED"}
PENDING_REVIEWERS = {"", "pending", "tbd", "n/a", "none"}
RUNTIME_EVIDENCE_VALUES = {"PROVEN", "NOT_PROVEN", "NOT_APPLICABLE"}
E2E_PRODUCT_VALUES = {"PASS", "FAIL", "PARTIAL", "BLOCKED", "NOT_PROVEN"}
RUNTIME_KINDS = ("live", "manual", "human", "script")
READ_ONLY_EVIDENCE_KINDS = ("commit", "ci", "run", "pytest", "artifact")
ALL_EVIDENCE_KINDS = READ_ONLY_EVIDENCE_KINDS + RUNTIME_KINDS

REQUIRED_FIELDS = (
    "id",
    "issue",
    "priority",
    "title",
    "requirement",
    "invariant",
    "status",
    "owner",
    "acceptance",
)
REQUIRED_ACCEPTANCE_FIELDS = ("status", "reviewed_at", "artifact")
STATUS_TOKEN_RE = re.compile(
    r"\b(PASS|PASSED|FAIL|FAILED|BLOCKED|PARTIAL|NOT_RUN|COMPLETED|APPROVED|ACTIVE|"
    r"VERIFIED|REJECTED|CANDIDATE)\b",
    re.IGNORECASE,
)
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
SCRIPT_RE = re.compile(r"^(?P<path>[^\s]+)(?:\s+.*)?$")
ARTIFACT_RE = re.compile(r"^(?P<path>[^\s]+)(?:\s+.*)?$")
REVIEW_ARTIFACT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt", ".log", ".html"}


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


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_repo_path(raw: str) -> Path | None:
    """按仓库根 / 后端根解析路径，返回首个存在项。"""
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return None
    candidates = [
        REPO_ROOT / text,
        BACKEND_ROOT / text,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _count_test_defs(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - 读失败按 0 处理
        return 0
    return len(re.findall(r"^\s*(?:async\s+)?def test_", text, re.MULTILINE))


def _load_matrix(path: Path, report: Report) -> dict[str, Any]:
    if not path.exists():
        report.error(f"追踪矩阵不存在: {_rel(path)}")
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
    resolved = _resolve_repo_path(file_part)
    if resolved is None:
        report.error(f"{issue_id}: 测试文件不存在: {file_part}")
        return None
    body = resolved.read_text(encoding="utf-8")
    if not re.search(rf"^\s*(?:async\s+)?def {re.escape(name)}\(", body, re.MULTILINE) and not re.search(
        rf"^\s*class {re.escape(name)}\b", body, re.MULTILINE
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
    if _resolve_repo_path(raw) is None:
        report.error(f"{issue_id}: code path 不存在: {raw}")
        return False
    return True


# --------------------------------------------------------------------------- #
# 证据校验（按类型）
# --------------------------------------------------------------------------- #


def _validate_commit_evidence(value: str, entry: dict[str, Any], report: Report) -> bool:
    if not SHA_RE.match(value):
        report.error(f"{entry.get('id')}: commit 证据必须是 7-40 位十六进制 SHA: {value!r}")
        return False
    return True


def _validate_ci_evidence(value: str, entry: dict[str, Any], report: Report) -> bool:
    if not value.strip():
        report.error(f"{entry.get('id')}: ci 证据不能为空")
        return False
    return True


def _validate_run_evidence(value: str, entry: dict[str, Any], report: Report) -> bool:
    if not value.strip():
        report.error(f"{entry.get('id')}: run 证据不能为空")
        return False
    if not UUID_RE.search(value) and not re.search(r"[A-Za-z0-9]{6,}", value):
        report.warn(f"{entry.get('id')}: run 证据缺少可识别的 Run ID: {value!r}")
    return True


def _validate_pytest_evidence(value: str, entry: dict[str, Any], report: Report) -> bool:
    text = value.strip()
    count_match = re.search(r"\(\s*(\d+)\s+passed\s*\)", text)
    target = text[: count_match.start()].strip() if count_match else text
    if not target:
        report.error(f"{entry.get('id')}: pytest 证据缺少文件路径: {value!r}")
        return False
    name = ""
    if "::" in target:
        target, name = target.split("::", 1)
        name = name.strip()
    if not target.endswith(".py"):
        report.error(f"{entry.get('id')}: pytest 证据必须是 .py 文件: {value!r}")
        return False
    resolved = _resolve_repo_path(target)
    if resolved is None:
        report.error(f"{entry.get('id')}: pytest 证据文件不存在: {target}")
        return False
    body = resolved.read_text(encoding="utf-8", errors="ignore")
    if name and not re.search(rf"^\s*(?:async\s+)?def {re.escape(name)}\(", body, re.MULTILINE):
        report.error(f"{entry.get('id')}: pytest 证据中的测试函数不存在: {target}::{name}")
        return False
    defined = _count_test_defs(resolved)
    if defined <= 0:
        report.error(f"{entry.get('id')}: pytest 证据文件没有任何 def test_: {target}")
        return False
    if count_match is None:
        if name:
            return True
        report.warn(f"{entry.get('id')}: pytest 证据建议记录通过数: {value!r}")
        return True
    count = int(count_match.group(1))
    if count <= 0:
        report.error(f"{entry.get('id')}: pytest 通过数必须大于 0: {value!r}")
        return False
    if count > defined * 5:
        report.error(
            f"{entry.get('id')}: pytest 通过数 {count} 与文件内 {defined} 个测试函数明显不符: {target}"
        )
        return False
    return True


def _validate_script_evidence(value: str, entry: dict[str, Any], report: Report) -> bool:
    match = SCRIPT_RE.match(value)
    if not match:
        report.error(f"{entry.get('id')}: script 证据必须是 'script:<repo-relative path>': {value!r}")
        return False
    if _resolve_repo_path(match.group("path")) is None:
        report.error(f"{entry.get('id')}: script 证据路径不存在: {match.group('path')}")
        return False
    return True


def _validate_runtime_evidence(value: str, entry: dict[str, Any], report: Report) -> bool:
    """live/manual/human：必须有可判读结论；artifact 声明在 runtime_evidence 块。"""
    ok = True
    status = str(entry.get("status") or "").strip().upper()
    if (
        status in PASSING_STATUS
        and not STATUS_TOKEN_RE.search(value)
        and "=" not in value
    ):
        report.warn(
            f"{entry.get('id')}: {value.split(':', 1)[0]} 证据缺少 PASS/FAIL/BLOCKED 等结论或 key=value: {value!r}"
        )
        ok = False
    if not isinstance(entry.get("runtime_evidence"), dict):
        report.error(f"{entry.get('id')}: 存在 {value.split(':', 1)[0]} 证据时必须声明 runtime_evidence")
        return False
    return ok


def _validate_artifact_evidence(value: str, entry: dict[str, Any], report: Report) -> bool:
    match = ARTIFACT_RE.match(value)
    if not match:
        report.error(f"{entry.get('id')}: artifact 证据必须是 'artifact:<repo-relative path>': {value!r}")
        return False
    if _resolve_repo_path(match.group("path")) is None:
        report.error(f"{entry.get('id')}: artifact 证据路径不存在: {match.group('path')}")
        return False
    return True


EVIDENCE_VALIDATORS: dict[str, Callable[[str, dict[str, Any], Report], bool]] = {
    "commit": _validate_commit_evidence,
    "ci": _validate_ci_evidence,
    "run": _validate_run_evidence,
    "pytest": _validate_pytest_evidence,
    "script": _validate_script_evidence,
    "live": _validate_runtime_evidence,
    "manual": _validate_runtime_evidence,
    "human": _validate_runtime_evidence,
    "artifact": _validate_artifact_evidence,
}


def _split_evidence(raw: str) -> tuple[str, str] | None:
    text = str(raw or "").strip()
    if ":" not in text:
        return None
    kind, value = text.split(":", 1)
    return kind.strip().lower(), value.strip()


# --------------------------------------------------------------------------- #
# 结构化字段校验
# --------------------------------------------------------------------------- #


def _validate_acceptance(entry: dict[str, Any], report: Report) -> None:
    req_id = str(entry.get("id") or "?")
    acceptance = entry.get("acceptance")
    if not isinstance(acceptance, dict):
        report.error(f"{req_id}: 缺少 acceptance 块（status/reviewed_at/artifact）")
        return
    for key in REQUIRED_ACCEPTANCE_FIELDS:
        if key not in acceptance:
            report.error(f"{req_id}: acceptance 缺少字段 {key}")
    status = str(acceptance.get("status") or "").strip().upper()
    reviewer = str(entry.get("reviewer") or "").strip()
    owner = str(entry.get("owner") or "").strip()
    if status not in ACCEPTANCE_VALUES:
        report.error(f"{req_id}: 非法 acceptance.status {status!r}（允许 {sorted(ACCEPTANCE_VALUES)}）")
        return
    if status == "NOT_REVIEWED":
        return
    if reviewer.lower() in PENDING_REVIEWERS:
        report.error(f"{req_id}: acceptance.status={status} 需要具体 Reviewer（当前 {reviewer!r}）")
    if reviewer and owner and reviewer == owner:
        report.error(f"{req_id}: acceptance.status={status} 不允许 Owner 自审（{owner!r}）")
    artifact = str(acceptance.get("artifact") or "").strip()
    if not artifact:
        report.error(f"{req_id}: acceptance.status={status} 需要 acceptance.artifact")
    else:
        resolved = _resolve_repo_path(artifact)
        if resolved is None:
            report.error(f"{req_id}: acceptance.artifact 不存在: {artifact}")
        elif resolved.suffix.lower() not in REVIEW_ARTIFACT_SUFFIXES:
            report.error(f"{req_id}: acceptance.artifact 必须是文档/JSON 记录: {artifact}")
    reviewed_at = str(acceptance.get("reviewed_at") or "").strip()
    if status == "REVIEWED":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_at):
            report.error(f"{req_id}: acceptance.reviewed_at 必须是 YYYY-MM-DD（当前 {reviewed_at!r}）")
        else:
            try:
                date.fromisoformat(reviewed_at)
            except ValueError:
                report.error(f"{req_id}: acceptance.reviewed_at 不是合法日期: {reviewed_at}")
    if status == "WAIVED":
        for key in ("waiver_reason", "waived_by"):
            if not str(acceptance.get(key) or "").strip():
                report.error(f"{req_id}: acceptance.status=WAIVED 需要 {key}")


def _validate_runtime_evidence_block(
    entry: dict[str, Any], report: Report, *, has_runtime_kind: bool
) -> None:
    req_id = str(entry.get("id") or "?")
    block = entry.get("runtime_evidence")
    if block is None:
        if has_runtime_kind:
            report.error(
                f"{req_id}: 含 live/manual/human/script 证据时必须声明 runtime_evidence"
            )
        return
    if not isinstance(block, dict):
        report.error(f"{req_id}: runtime_evidence 必须是对象")
        return
    status = str(block.get("status") or "").strip().upper()
    if status not in RUNTIME_EVIDENCE_VALUES:
        report.error(f"{req_id}: 非法 runtime_evidence.status {status!r}")
        return
    if status == "NOT_APPLICABLE" and has_runtime_kind:
        report.error(f"{req_id}: 存在运行时证据时 runtime_evidence 不得为 NOT_APPLICABLE")
    if status == "NOT_PROVEN":
        if not str(block.get("note") or "").strip():
            report.error(f"{req_id}: runtime_evidence.status=NOT_PROVEN 需要 note 说明缺什么")
        return
    if status != "PROVEN":
        return
    artifacts = block.get("artifacts") or []
    if not isinstance(artifacts, list) or not artifacts:
        report.error(f"{req_id}: runtime_evidence.status=PROVEN 需要非空 artifacts 列表")
        return
    for artifact in artifacts:
        if _resolve_repo_path(str(artifact)) is None:
            report.error(f"{req_id}: runtime_evidence artifact 不存在: {artifact}")
    refs = block.get("refs")
    if not isinstance(refs, dict) or not refs:
        report.error(f"{req_id}: runtime_evidence.status=PROVEN 需要 refs（run_id/job_ids/...）")
        return
    if not (refs.get("run_id") or refs.get("run_ids")):
        report.error(f"{req_id}: runtime_evidence.refs 必须包含 run_id 或 run_ids")


def _validate_e2e_block(
    entry: dict[str, Any],
    report: Report,
    *,
    status: str,
    priority: str,
) -> None:
    req_id = str(entry.get("id") or "?")
    if not PRODUCT_TC_RE.match(req_id):
        return
    block = entry.get("e2e")
    if not isinstance(block, dict):
        report.error(f"{req_id}: 产品 TC 必须声明 e2e.product / e2e.platform")
        return
    product = block.get("product")
    platform = block.get("platform") or {}
    if not isinstance(product, dict):
        report.error(f"{req_id}: e2e.product 必须是对象")
        return
    product_status = str(product.get("status") or "").strip().upper()
    if product_status not in E2E_PRODUCT_VALUES:
        report.error(f"{req_id}: 非法 e2e.product.status {product_status!r}")
    evidence = product.get("evidence") or []
    if not isinstance(evidence, list):
        report.error(f"{req_id}: e2e.product.evidence 必须是数组")
        evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            report.error(f"{req_id}: e2e.product.evidence 每项必须是对象")
            continue
        kind = str(item.get("kind") or "").strip()
        if kind not in {"artifact", "owner-attested", "report"}:
            report.error(f"{req_id}: 非法 e2e.product.evidence.kind {kind!r}")
        ref = str(item.get("ref") or "").strip()
        if kind == "artifact":
            if _resolve_repo_path(ref) is None:
                report.error(f"{req_id}: 产品 TC artifact 不存在: {ref}")
    if product_status == "PASS":
        if not any(str(item.get("kind")) == "artifact" for item in evidence if isinstance(item, dict)):
            report.error(f"{req_id}: e2e.product.status=PASS 需要归档 artifact，不能只用现场记录")
        runtime = entry.get("runtime_evidence") or {}
        if str(runtime.get("status") or "").upper() != "PROVEN":
            report.error(f"{req_id}: e2e.product.status=PASS 需要 runtime_evidence.status=PROVEN")
    if status in {"VERIFIED", "ACCEPTED"} and product_status != "PASS":
        report.error(
            f"{req_id}: 产品 TC 为 {status} 时 e2e.product.status 必须为 PASS（当前 {product_status or '未声明'}）"
        )
    tc_ids = platform.get("tc_ids") or []
    if not isinstance(tc_ids, list):
        report.error(f"{req_id}: e2e.platform.tc_ids 必须是数组")
        tc_ids = []
    for tc_id in tc_ids:
        if not PLATFORM_TC_RE.match(str(tc_id)):
            report.error(f"{req_id}: 非法平台 TC ID {tc_id!r}（必须是 TC-PLATFORM-xxx）")
    platform_tests = platform.get("tests") or []
    if not isinstance(platform_tests, list):
        report.error(f"{req_id}: e2e.platform.tests 必须是数组")
    else:
        for test in platform_tests:
            _parse_test_ref(str(test), report, issue_id=req_id)


def _validate_baseline(matrix: dict[str, Any], report: Report, *, check_git: bool) -> None:
    baseline = matrix.get("baseline")
    if not isinstance(baseline, dict):
        report.error("追踪矩阵缺少 baseline")
        return
    for key in ("release_commit", "migration_head", "branch"):
        if not str(baseline.get(key) or "").strip():
            report.error(f"baseline 缺少字段 {key}")
    commit = str(baseline.get("release_commit") or "").strip().lower()
    if commit and not re.fullmatch(r"[0-9a-f]{40}", commit):
        report.error(f"baseline.release_commit 必须是完整 40 位 SHA: {commit!r}")
    if not check_git:
        return
    if commit:
        exists = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if exists.returncode != 0:
            report.error(f"baseline.release_commit 在仓库中不存在: {commit}")
        else:
            ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            if ancestor.returncode != 0:
                report.warn(
                    f"baseline.release_commit {commit[:12]} 不是当前 HEAD 的祖先（PR 分支正常；发布时需同步）"
                )
    actual_head = _compute_alembic_head(report)
    recorded = str(baseline.get("migration_head") or "").strip()
    if actual_head and recorded and actual_head != recorded:
        report.error(
            f"baseline.migration_head 过期: 记录 {recorded} / 实际 {actual_head}（必须指向单一当前 head）"
        )


def _parse_down_revision(text: str) -> str | tuple[str, ...] | None:
    match = re.search(r"^down_revision(?::\s*[^=]+)?\s*=\s*(.+)$", text, re.MULTILINE)
    if not match:
        return None
    remainder = match.group(1)
    offset = match.end()
    # 多行 tuple：把括号补齐前的后续行一起纳入解析。
    while remainder.count("(") > remainder.count(")") and offset < len(text):
        newline = text.find("\n", offset)
        if newline == -1:
            break
        line = text[newline + 1 :].splitlines()[0] if text[newline + 1 :].splitlines() else ""
        remainder += " " + line
        offset = newline + 1 + len(line)
    names = re.findall(r"['\"]([^'\"]+)['\"]", remainder)
    if not names:
        return None
    if len(names) == 1 and "(" not in remainder:
        return names[0]
    return tuple(names)


def _compute_alembic_head(report: Report) -> str:
    if not ALEMBIC_VERSIONS.exists():
        return ""
    revisions: dict[str, str | tuple[str, ...] | None] = {}
    referenced: set[str] = set()
    for path in sorted(ALEMBIC_VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        revision_match = re.search(r"^revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE)
        if not revision_match:
            continue
        revision = revision_match.group(1)
        down = _parse_down_revision(text)
        revisions[revision] = down
        if isinstance(down, str):
            referenced.add(down)
        elif isinstance(down, tuple):
            referenced.update(down)
    heads = [revision for revision in revisions if revision not in referenced]
    if len(heads) != 1:
        report.error(f"Alembic head 不唯一: {sorted(heads)}")
        return heads[0] if len(heads) == 1 else ""
    return heads[0]


# --------------------------------------------------------------------------- #
# 需求条目校验
# --------------------------------------------------------------------------- #


def _validate_requirement(
    entry: dict[str, Any], report: Report, seen_ids: set[str]
) -> dict[str, Any]:
    for field_name in REQUIRED_FIELDS:
        if field_name == "acceptance":
            continue
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
    has_runtime_kind = False
    runtime_evidence_ok = True
    for item in evidence:
        split = _split_evidence(str(item or ""))
        if split is None:
            report.error(
                f"{req_id}: evidence 必须使用类型前缀 "
                f"({'/'.join(ALL_EVIDENCE_KINDS)}): {item!r}"
            )
            continue
        kind, value = split
        if kind not in EVIDENCE_VALIDATORS:
            report.error(f"{req_id}: 未知 evidence 类型 {kind!r}: {item!r}")
            continue
        if kind in RUNTIME_KINDS:
            has_runtime_kind = True
        if not value:
            report.error(f"{req_id}: evidence 值为空: {item!r}")
            continue
        ok = EVIDENCE_VALIDATORS[kind](value, entry, report)
        if kind in RUNTIME_KINDS and not ok:
            runtime_evidence_ok = False

    _validate_runtime_evidence_block(entry, report, has_runtime_kind=has_runtime_kind)
    _validate_acceptance(entry, report)

    layers = entry.get("layers") or []
    if not isinstance(layers, list):
        report.error(f"{req_id}: layers 必须是数组")
        layers = []
    for layer in layers:
        if str(layer) not in {"L1", "L2", "L3", "L4"}:
            report.error(f"{req_id}: 非法测试层级 {layer!r}")

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
        pytest_evidence = [
            item for item in evidence if str(item).lower().startswith("pytest:")
        ]
        if has_runtime_kind and not pytest_evidence:
            report.error(
                f"{req_id}: {status} 不能只靠 live/manual/human/script 证据（必须有仓库内 pytest 证据或降级为 PARTIAL）"
            )
        if has_runtime_kind and not runtime_evidence_ok:
            report.warn(f"{req_id}: {status} 的运行时证据缺少可判读结论")
    if status == "ACCEPTED":
        acceptance = entry.get("acceptance") or {}
        if str(acceptance.get("status") or "").upper() != "REVIEWED":
            report.error(f"{req_id}: ACCEPTED 需要 acceptance.status=REVIEWED")
        if str(entry.get("reviewer") or "").strip().lower() in PENDING_REVIEWERS or (
            entry.get("reviewer") == owner
        ):
            report.error(f"{req_id}: ACCEPTED 需要非原作者的独立 reviewer（当前 {entry.get('reviewer')!r}）")
    if status == "IMPLEMENTED" and not code_entries:
        report.error(f"{req_id}: IMPLEMENTED 需要代码映射")
    if status == "BLOCKED":
        for required in ("blocked_reason", "owner", "review_by"):
            if not str(entry.get(required) or "").strip():
                report.error(f"{req_id}: BLOCKED 必须填写 {required}")

    _validate_e2e_block(entry, report, status=status, priority=priority)

    entry["_parsed_tests"] = parsed_tests
    entry["_status"] = status
    entry["_priority"] = priority
    entry["_runtime_evidence_ok"] = runtime_evidence_ok
    entry["_has_runtime_kind"] = has_runtime_kind
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
    platform_ids = {
        str(tc_id)
        for entry in entries
        for tc_id in ((entry.get("e2e") or {}).get("platform") or {}).get("tc_ids") or []
    }
    if len(platform_ids) != len({str(tc) for tc in platform_ids}):
        report.warn("平台 TC ID 存在重复引用")
    return by_issue


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0




# --------------------------------------------------------------------------- #
# PR 模式
# --------------------------------------------------------------------------- #

PR_REQUIRED_FIELDS = (
    "Issue / Requirement ID",
    "业务结果",
    "正式入口",
    "调用链",
    "真实组件与 Mock 边界",
    "成功路径测试",
    "拒绝/失败路径测试",
    "证据",
    "Reviewer",
)
PR_PLACEHOLDER_TOKENS = ("例如", "<!--", "path::test_name", "请填写", "todo", "tbd")


def _parse_pr_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines():
        match = re.match(r"^\s*(?:-\s*)?(?P<key>[^：:]{2,120})[：:]\s*(?P<value>.*)$", line)
        if not match:
            continue
        key = match.group("key").strip()
        value = match.group("value").strip()
        if key not in fields or not fields[key]:
            fields[key] = value
    return fields


def _find_field(fields: dict[str, str], required: str) -> tuple[str, str]:
    for key, value in fields.items():
        if key.startswith(required) or required in key:
            return key, value
    return "", ""


def _validate_pr_fields(body: str, report: Report, *, pr_author: str) -> None:
    fields = _parse_pr_fields(body)
    for required in PR_REQUIRED_FIELDS:
        matched_key, matched_value = _find_field(fields, required)
        if not matched_key:
            report.error(f"PR 描述缺少字段: {required}")
            continue
        value = matched_value.strip()
        if not value:
            report.error(f"PR 字段未填写: {matched_key}")
            continue
        lowered = value.lower()
        if any(token in value for token in PR_PLACEHOLDER_TOKENS) or lowered in {"...", "…", "-"}:
            report.error(f"PR 字段仍是占位符: {matched_key} = {value!r}")
            continue
        if len(value) < 8 and required not in {"Reviewer"}:
            report.error(f"PR 字段内容过短: {matched_key} = {value!r}")
    _, evidence_value_raw = _find_field(fields, "证据")
    evidence_value = evidence_value_raw.strip()
    if evidence_value and not re.search(
        r"(commit:|ci:|run:|pytest:|artifact:|live:|manual:|[0-9a-f]{7,40})", evidence_value
    ):
        report.error(f"PR 证据字段缺少可识别证据（commit:/ci:/run:/pytest:/artifact:）: {evidence_value!r}")
    _, reviewer_raw = _find_field(fields, "Reviewer")
    reviewer = reviewer_raw.strip()
    if reviewer:
        if reviewer.lower() in PENDING_REVIEWERS:
            report.warn("PR Reviewer 仍为 pending；P0/P1 合入前需要非原作者签署")
        if pr_author and reviewer.lstrip("@").lower() == pr_author.lstrip("@").lower():
            report.error(f"PR Reviewer 不能是 PR 作者本人: {reviewer!r}")
    for key in ("成功路径测试", "拒绝/失败路径测试"):
        _, value = _find_field(fields, key)
        if not value:
            continue
        for token in re.split(r"[,，;\s]+", value):
            if "::" in token:
                _parse_test_ref(token, report, issue_id=f"PR:{key}")


def _pr_mode(
    entries: list[dict[str, Any]],
    args: argparse.Namespace,
    report: Report,
) -> None:
    issue_ids = [str(item).strip() for item in (args.issue or []) if str(item).strip()]
    if not issue_ids and not args.pr_body:
        return
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
            _validate_pr_fields(body, report, pr_author=str(args.pr_author or ""))
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
        relevant_prefixes = {
            "test-platform-v2/backend/tests",
            "test-platform-v2/backend/alembic/versions",
            "docs/aiqe/v1.6",
            "scripts/aiqe",
            "scripts/qa",
            "scripts/ci",
            ".github",
            "work-logs",
        }
        for path in changed:
            if path in mapped:
                continue
            if any(path.startswith(prefix) for prefix in relevant_prefixes):
                continue
            report.warn(f"变更文件未被追踪矩阵 code 映射覆盖: {path}")


# --------------------------------------------------------------------------- #
# 发布门禁
# --------------------------------------------------------------------------- #


def _release_gate(entries: list[dict[str, Any]], report: Report) -> None:
    pending_acceptance = [
        str(item.get("id"))
        for item in entries
        if str(item.get("_priority")) in P0_P1
        and str((item.get("acceptance") or {}).get("status") or "").upper() != "REVIEWED"
    ]
    if pending_acceptance:
        report.error(
            "release-gate: P0/P1 仍有未独立验收条目 "
            f"({len(pending_acceptance)} 条): {', '.join(pending_acceptance[:12])}"
            + (" ..." if len(pending_acceptance) > 12 else "")
        )
    unproven_runtime = [
        str(item.get("id"))
        for item in entries
        if str(item.get("_priority")) in P0_P1
        and str(((item.get("runtime_evidence") or {}).get("status") or "")).upper() == "NOT_PROVEN"
    ]
    if unproven_runtime:
        report.error(
            "release-gate: P0/P1 运行时证据未归档（NOT_PROVEN）"
            f" ({len(unproven_runtime)} 条): {', '.join(unproven_runtime[:12])}"
        )
    product_tcs = [item for item in entries if PRODUCT_TC_RE.match(str(item.get("id")))]
    not_pass = [
        str(item.get("id"))
        for item in product_tcs
        if str(((item.get("e2e") or {}).get("product") or {}).get("status") or "").upper() != "PASS"
    ]
    if not_pass:
        report.error(
            "release-gate: 产品级 TC 未达 PASS，不得宣称 10/10 "
            f"({len(not_pass)}/10): {', '.join(not_pass)}"
        )
    verified_without_runtime = [
        str(item.get("id"))
        for item in entries
        if str(item.get("_status")) in PASSING_STATUS
        and item.get("_has_runtime_kind")
        and not any(str(ev).lower().startswith("pytest:") for ev in (item.get("evidence") or []))
    ]
    if verified_without_runtime:
        report.error(
            "release-gate: 以下条目仅凭运行时记录即标 VERIFIED/ACCEPTED: "
            + ", ".join(verified_without_runtime)
        )


# --------------------------------------------------------------------------- #
# 生成产物
# --------------------------------------------------------------------------- #


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
    """矩阵快照（**不是**运行证据）。

    V16-023 的真实运行证据必须由 ``scripts/aiqe/build_evidence_index.py`` 从测试
    产物生成；本函数只输出“矩阵声明了什么”，并显式标记 not_runtime_evidence。
    """
    baseline = matrix.get("baseline") or {}
    payload = {
        "schema_version": "2.0",
        "artifact_kind": "traceability-matrix-snapshot",
        "not_runtime_evidence": True,
        "note": (
            "本文件由追踪矩阵派生，只表示矩阵声明；运行证据请使用 "
            "scripts/aiqe/build_evidence_index.py 从测试产物生成。"
        ),
        "release": matrix.get("release", "aiqe-v1.6"),
        "commit_sha": args.commit_sha or _git_sha(),
        "ci_run": args.ci_run or "",
        "environment": args.environment or "local",
        "baseline": {
            "release_commit": baseline.get("release_commit"),
            "migration_head": baseline.get("migration_head"),
            "prior_audit_snapshot_sha": baseline.get("prior_audit_snapshot_sha"),
        },
        "summary": {
            "requirements": len(entries),
            "verified": sum(1 for item in entries if item.get("_status") in PASSING_STATUS),
            "accepted": sum(
                1
                for item in entries
                if str((item.get("acceptance") or {}).get("status") or "").upper() == "REVIEWED"
            ),
            "partial": sum(1 for item in entries if item.get("_status") == "PARTIAL"),
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
                "acceptance": item.get("acceptance") or {},
                "runtime_evidence": item.get("runtime_evidence") or {},
                "e2e": item.get("e2e") or {},
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
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


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
    reviewed = sum(
        1
        for item in ordered
        if str((item.get("acceptance") or {}).get("status") or "").upper() == "REVIEWED"
    )
    lines: list[str] = []
    lines.append("# CamelTv AIQE V1.6 需求—代码—正式入口—测试—证据矩阵")
    lines.append("")
    lines.append("> 本文件由 `python scripts/aiqe/check_traceability.py --emit-markdown` 从")
    lines.append("> `docs/aiqe/v1.6/traceability/requirements.yaml` 生成，**禁止手工编辑**。")
    lines.append("> 状态语义：`NOT_STARTED` / `PARTIAL` / `IMPLEMENTED` 不计入交付通过率；")
    lines.append("> `VERIFIED` 表示交付/自动证据成立，`ACCEPTED` 还需 `acceptance.status=REVIEWED`。")
    lines.append("> 独立验收与运行时证据状态见 `acceptance` / `runtime_evidence` 列。")
    lines.append("")
    lines.append("## 基线（唯一）")
    lines.append("")
    lines.append(f"- release: `{matrix.get('release', 'aiqe-v1.6')}`")
    lines.append(f"- release commit: `{baseline.get('release_commit', '')}`")
    lines.append(f"- 迁移 head: `{baseline.get('migration_head', '')}`")
    lines.append(f"- 分支: `{baseline.get('branch', '')}`")
    lines.append(f"- 上一轮审计快照: `{baseline.get('prior_audit_snapshot_sha', '')}`")
    lines.append("")
    lines.append("## 状态汇总")
    lines.append("")
    lines.append("| 状态 | 数量 |")
    lines.append("|---|---:|")
    for status in ("VERIFIED", "ACCEPTED", "IMPLEMENTED", "PARTIAL", "NOT_STARTED", "BLOCKED"):
        lines.append(f"| {status} | {status_counts.get(status, 0)} |")
    lines.append(f"| **合计** | **{len(ordered)}** |")
    lines.append(f"| 已独立验收（acceptance=REVIEWED） | {reviewed} |")
    lines.append("")
    lines.append("## 需求追踪")
    lines.append("")
    lines.append(
        "| Requirement | Issue | 优先级 | 状态 | Owner | Reviewer | 验收 | 运行时证据 | 正式入口 | 成功/拒绝测试 | 层级 | 证据 | 未决风险 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
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
        acceptance = item.get("acceptance") or {}
        acceptance_text = str(acceptance.get("status") or "")
        if acceptance_text == "REVIEWED":
            acceptance_text = f"REVIEWED/{item.get('reviewer')}"
        runtime = (item.get("runtime_evidence") or {}).get("status") or "—"
        lines.append(
            "| {id} | {issue} | {priority} | {status} | {owner} | {reviewer} | {acceptance} | {runtime} | {entry} | {tests} | {layers} | {evidence} | {gaps} |".format(
                id=item.get("id"),
                issue=item.get("issue"),
                priority=item.get("_priority"),
                status=item.get("_status"),
                owner=item.get("owner"),
                reviewer=item.get("reviewer") or "pending",
                acceptance=acceptance_text,
                runtime=runtime,
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
        lines.append(
            f"- Issue: `{item.get('issue')}` / 优先级 `{item.get('_priority')}` / 状态 `{item.get('_status')}`"
        )
        lines.append(f"- 需求：{item.get('requirement')}")
        lines.append(f"- 不变量：{item.get('invariant')}")
        acceptance = item.get("acceptance") or {}
        lines.append(
            f"- 独立验收：`{acceptance.get('status')}` / reviewer `{item.get('reviewer')}` / "
            f"artifact `{acceptance.get('artifact')}`"
        )
        runtime = item.get("runtime_evidence") or {}
        if runtime:
            lines.append(f"- 运行时证据：`{runtime.get('status')}`（{runtime.get('note') or '已归档'}）")
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
        e2e = item.get("e2e") or {}
        if e2e:
            product = e2e.get("product") or {}
            platform = e2e.get("platform") or {}
            lines.append(
                f"- 产品级 E2E：`{product.get('status')}`；平台 TC：{', '.join(platform.get('tc_ids') or []) or '—'}"
            )
        if item.get("mock_boundary"):
            lines.append(f"- Mock 边界：{item.get('mock_boundary')}")
        if item.get("evidence"):
            lines.append(f"- 证据：{'；'.join(str(x) for x in item.get('evidence'))}")
        lines.append("")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIQE V1.6 追踪矩阵门禁")
    parser.add_argument("--matrix", default=str(MATRIX_PATH))
    parser.add_argument("--issue", action="append", default=[])
    parser.add_argument("--pr-body", default="")
    parser.add_argument("--changed-files", default="")
    parser.add_argument("--pr-author", default="")
    parser.add_argument("--emit-evidence-index", default="")
    parser.add_argument("--emit-markdown", default="")
    parser.add_argument("--commit-sha", default="")
    parser.add_argument("--ci-run", default="")
    parser.add_argument("--environment", default="")
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument("--check-baseline", action="store_true")
    parser.add_argument("--release-gate", action="store_true")
    parser.add_argument("--summary", default="")
    args = parser.parse_args(argv)

    report = Report()
    matrix_file = Path(args.matrix)
    matrix = _load_matrix(matrix_file, report)
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
    _validate_baseline(matrix, report, check_git=bool(args.check_baseline))
    if args.issue or args.pr_body:
        _pr_mode(entries, args, report)
    if args.release_gate:
        _release_gate(entries, report)

    if args.emit_evidence_index:
        _emit_evidence_index(matrix, entries, Path(args.emit_evidence_index), args)
    if args.emit_markdown:
        _emit_markdown(matrix, entries, Path(args.emit_markdown))

    summary = {
        "requirements": len(entries),
        "verified": sum(1 for item in entries if item.get("_status") in PASSING_STATUS),
        "accepted": sum(
            1
            for item in entries
            if str((item.get("acceptance") or {}).get("status") or "").upper() == "REVIEWED"
        ),
        "partial": sum(1 for item in entries if item.get("_status") == "PARTIAL"),
        "blocked": sum(1 for item in entries if item.get("_status") == "BLOCKED"),
        "not_started": sum(1 for item in entries if item.get("_status") == "NOT_STARTED"),
        "runtime_not_proven": sum(
            1
            for item in entries
            if str(((item.get("runtime_evidence") or {}).get("status") or "")).upper() == "NOT_PROVEN"
        ),
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
