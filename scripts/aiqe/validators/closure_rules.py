"""FIX-012 审计关闭规则注册表：把“文件存在”升级为“语义证据验证”。

每个审计条目必须声明 ``closure_rule_id``；``CLOSED`` 只能由本模块的规则证明。
规则只读取仓库内真实事实（配置、执行结果、运行时索引、扫描报告、Ruleset 导出、
测试代码），不允许把“路径存在”“note 非空”当作关闭依据。

规则状态语义（复用 ``statuses``）：
- ``PASS``：本次语义验证通过，且证据可追溯；
- ``FAIL``：证据之间互相矛盾 / 明确不满足要求（必须阻断关闭）；
- ``NOT_PROVEN``：证据缺失、过期或不足，无法证明（不得关闭）。

CLOSED 还必须同时满足 ``check_audit_closure`` 的结构要求：真实
``verified_commit_sha``、可执行 verifier（名称/版本/CI Run）、artifact hash、
``verified_at`` 与真实 GitHub review 身份。
"""
from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover - 脚本/测试两条加载路径
    sys.path.insert(0, str(SCRIPT_DIR))
from statuses import FAIL, NOT_PROVEN, PASS  # noqa: E402
from validators.branch import AIQE_AGGREGATE_CHECK, validate_branch_protection  # noqa: E402
from validators.common import (  # noqa: E402
    is_sha,
    parse_time,
    resolve_repo_path,
    sha256_file,
)
from validators.product_tc import (  # noqa: E402
    TC_IDS,
    runner_is_declared,
    validate_product_config,
    validate_product_results,
)
from validators.provenance import validate_provenance  # noqa: E402
from validators.runtime_index import validate_runtime_index  # noqa: E402

DEFAULT_PRODUCT_CONFIG = "docs/aiqe/v1.6/e2e/product-tc-config.yaml"
DEFAULT_PRODUCT_RESULTS = "docs/aiqe/v1.6/e2e/product-results.json"
DEFAULT_MATRIX = "docs/aiqe/v1.6/traceability/requirements.yaml"
DEFAULT_COVERAGE = "docs/aiqe/v1.6/E2E-Coverage-and-Blockers.md"
DEFAULT_RUNTIME_INDEX = "docs/aiqe/v1.6/evidence/evidence-index.json"
DEFAULT_PLATFORM_RESULTS = "docs/aiqe/v1.6/e2e/platform-results.json"
DEFAULT_CREDENTIAL_SCAN = "docs/aiqe/v1.6/evidence/credential-scan.json"
DEFAULT_BRANCH_PROTECTION = "docs/aiqe/v1.6/governance/branch-protection.json"
COVERAGE_CLAIM_RE = re.compile(r"产品级\s*TC\s*PASS\s*[：:]\s*(\d+)\s*/\s*(\d+)")
DOTTED_INDEX_RE = re.compile(r"^(.*?)\[(\d+)\]$")


class RuleExecutionError(RuntimeError):
    """规则自身无法执行（输入格式非法等）；按 NOT_PROVEN 处理，绝不 PASS。"""


# ---------------------------------------------------------------------------
# 结果模型与注册表
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class RuleOutcome:
    rule_id: str
    verifier_name: str
    verifier_version: str
    conflicts: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    artifact_hashes: dict[str, str] = field(default_factory=dict)
    checks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.conflicts:
            return FAIL
        if self.gaps:
            return NOT_PROVEN
        return PASS

    @property
    def passed(self) -> bool:
        return self.status == PASS

    @property
    def reasons(self) -> list[str]:
        return self.conflicts + self.gaps

    def conflict(self, reason: str) -> "RuleOutcome":
        if str(reason).strip():
            self.conflicts.append(str(reason))
        return self

    def gap(self, reason: str) -> "RuleOutcome":
        if str(reason).strip():
            self.gaps.append(str(reason))
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "verifier": {"name": self.verifier_name, "version": self.verifier_version},
            "status": self.status,
            "conflicts": list(self.conflicts),
            "gaps": list(self.gaps),
            "evidence_refs": list(self.evidence_refs),
            "artifact_hashes": dict(self.artifact_hashes),
        }


@dataclass(slots=True)
class RuleInputs:
    """规则输入：仓库根 + 审计条目 + 期望 SHA。"""

    root: Path
    item: dict[str, Any]
    expected_commit: str = ""
    _json_cache: dict[str, Any] = field(default_factory=dict, repr=False)
    _yaml_cache: dict[str, Any] = field(default_factory=dict, repr=False)
    _text_cache: dict[str, str] = field(default_factory=dict, repr=False)

    def option(self, key: str, default: Any = None) -> Any:
        inputs = self.item.get("inputs") if isinstance(self.item.get("inputs"), dict) else {}
        if key in inputs:
            return inputs[key]
        return self.item.get(key, default)

    def path(self, rel: object) -> Path | None:
        return resolve_repo_path(self.root, rel)

    def read_json(self, rel: object) -> Any:
        text = str(rel or "")
        if text in self._json_cache:
            return self._json_cache[text]
        path = self.path(rel)
        if path is None or not path.is_file():
            raise RuleExecutionError(f"JSON 证据不存在或越界: {rel!r}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuleExecutionError(f"JSON 证据无法解析: {rel!r}: {exc}") from exc
        self._json_cache[text] = data
        return data

    def read_yaml(self, rel: object) -> Any:
        text = str(rel or "")
        if text in self._yaml_cache:
            return self._yaml_cache[text]
        path = self.path(rel)
        if path is None or not path.is_file():
            raise RuleExecutionError(f"YAML 证据不存在或越界: {rel!r}")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise RuleExecutionError(f"YAML 证据无法解析: {rel!r}: {exc}") from exc
        self._yaml_cache[text] = data
        return data

    def read_text(self, rel: object) -> str:
        text = str(rel or "")
        if text in self._text_cache:
            return self._text_cache[text]
        path = self.path(rel)
        if path is None or not path.is_file():
            raise RuleExecutionError(f"证据不存在或越界: {rel!r}")
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuleExecutionError(f"证据无法读取: {rel!r}: {exc}") from exc
        self._text_cache[text] = content
        return content

    def hash_path(self, rel: object) -> str | None:
        path = self.path(rel)
        if path is None or not path.is_file():
            return None
        return sha256_file(path)


ClosureRuleFunc = Callable[[RuleInputs], RuleOutcome]


@dataclass(frozen=True, slots=True)
class ClosureRule:
    rule_id: str
    description: str
    verifier_name: str
    verifier_version: str
    func: ClosureRuleFunc
    requires_verified_commit: bool = True

    def verify(self, inputs: RuleInputs) -> RuleOutcome:
        return self.func(inputs)


RULES: dict[str, ClosureRule] = {}


def register(rule: ClosureRule) -> ClosureRule:
    if rule.rule_id in RULES:
        raise ValueError(f"重复注册 closure rule: {rule.rule_id}")
    RULES[rule.rule_id] = rule
    return rule


def get_rule(rule_id: str) -> ClosureRule | None:
    return RULES.get(str(rule_id or "").strip())


def rule_ids() -> tuple[str, ...]:
    return tuple(RULES)


# ---------------------------------------------------------------------------
# 共享工具
# ---------------------------------------------------------------------------
def _evidence_paths(inputs: RuleInputs) -> list[str]:
    raw = inputs.item.get("evidence") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item).strip()]


def _hash_evidence(inputs: RuleInputs, outcome: RuleOutcome) -> None:
    for rel in _evidence_paths(inputs):
        digest = inputs.hash_path(rel)
        if digest:
            outcome.artifact_hashes[rel] = digest
            if rel not in outcome.evidence_refs:
                outcome.evidence_refs.append(rel)


def _load_required(
    inputs: RuleInputs, outcome: RuleOutcome, rel: object, label: str, *, kind: str
) -> Any:
    try:
        return inputs.read_json(rel) if kind == "json" else inputs.read_yaml(rel)
    except RuleExecutionError as exc:
        outcome.gap(f"{label}: {exc}")
        return None


def _pointer(data: Any, pointer: str) -> tuple[bool, Any]:
    """解析 ``a.b[0].c`` 形式的路径；返回（是否存在, 值）。"""
    if not pointer:
        return True, data
    current = data
    for chunk in pointer.split("."):
        match = DOTTED_INDEX_RE.match(chunk)
        index: int | None = None
        key = chunk
        if match:
            key, raw_index = match.group(1), match.group(2)
            index = int(raw_index)
        if key:
            if not isinstance(current, dict) or key not in current:
                return False, None
            current = current[key]
        if index is not None:
            if not isinstance(current, list) or index >= len(current):
                return False, None
            current = current[index]
    return True, current


def _verify_assertions(inputs: RuleInputs, outcome: RuleOutcome, assertions: Any) -> int:
    """执行内容级断言；返回通过的断言数（0 表示没有可执行断言）。"""
    if not isinstance(assertions, list) or not assertions:
        return 0
    executed = 0
    for index, raw in enumerate(assertions, 1):
        if not isinstance(raw, dict):
            outcome.gap(f"assertions[{index}] 必须是对象")
            continue
        rel = str(raw.get("path") or "").strip()
        if not rel:
            outcome.gap(f"assertions[{index}] 缺少 path")
            continue
        path = inputs.path(rel)
        if path is None or not path.is_file():
            outcome.conflict(f"断言目标不存在或越界: {rel}")
            continue
        digest = sha256_file(path)
        outcome.artifact_hashes[rel] = digest
        if rel not in outcome.evidence_refs:
            outcome.evidence_refs.append(rel)
        kind = str(raw.get("kind") or "").strip().lower()
        if not kind:
            suffix = path.suffix.lower()
            kind = "json" if suffix == ".json" else "yaml" if suffix in {".yaml", ".yml"} else "text"
        content_predicates = 0
        if kind == "text":
            text = inputs.read_text(rel)
            for token in raw.get("must_contain") or []:
                content_predicates += 1
                if str(token) not in text:
                    outcome.conflict(f"{rel} 缺少必需内容: {token!r}")
            for token in raw.get("must_not_contain") or []:
                content_predicates += 1
                if str(token) in text:
                    outcome.conflict(f"{rel} 出现禁止内容: {token!r}")
        elif kind in {"json", "yaml"}:
            try:
                data = inputs.read_json(rel) if kind == "json" else inputs.read_yaml(rel)
            except RuleExecutionError as exc:
                outcome.conflict(str(exc))
                continue
            pointer = str(raw.get("pointer") or "").strip()
            exists, value = _pointer(data, pointer)
            if not exists:
                outcome.conflict(f"{rel}#{pointer or '<root>'} 不存在")
                continue
            if "equals" in raw:
                content_predicates += 1
                if value != raw.get("equals"):
                    outcome.conflict(
                        f"{rel}#{pointer} 期望 {raw.get('equals')!r}，实际 {value!r}"
                    )
            if "in" in raw:
                content_predicates += 1
                allowed = raw.get("in") or []
                if value not in allowed:
                    outcome.conflict(f"{rel}#{pointer}={value!r} 不在允许集合 {allowed}")
            if "match" in raw:
                content_predicates += 1
                if not re.search(str(raw.get("match")), str(value if value is not None else "")):
                    outcome.conflict(
                        f"{rel}#{pointer}={value!r} 不匹配 {raw.get('match')!r}"
                    )
            if raw.get("truthy") is True:
                content_predicates += 1
                if not value:
                    outcome.conflict(f"{rel}#{pointer} 必须为真值，实际 {value!r}")
            if "contains" in raw:
                content_predicates += 1
                needle = str(raw.get("contains"))
                if not isinstance(value, str) or needle not in value:
                    outcome.conflict(f"{rel}#{pointer} 缺少必需内容: {needle!r}")
            if "min" in raw:
                content_predicates += 1
                try:
                    if float(value) < float(raw.get("min")):
                        outcome.conflict(f"{rel}#{pointer}={value!r} 小于下限 {raw.get('min')}")
                except (TypeError, ValueError):
                    outcome.conflict(f"{rel}#{pointer}={value!r} 不是数值，无法比较 min")
        else:
            outcome.gap(f"assertions[{index}] 不支持的 kind: {kind!r}")
            continue
        if content_predicates == 0:
            outcome.gap(f"assertions[{index}] 没有内容断言（不能只判断路径存在）")
        else:
            executed += 1
    return executed


def _gate_reasons(outcome: RuleOutcome, check: Any, *, label: str) -> None:
    """把 GateCheck 结果映射为规则冲突/缺口。"""
    if check is None:
        outcome.gap(f"{label}: 缺少校验结果")
        return
    status = str(getattr(check, "status", "") or "")
    reasons = list(getattr(check, "reasons", []) or [])
    if status == PASS:
        return
    target = outcome.conflict if status == FAIL else outcome.gap
    for reason in reasons or [f"{label} 未通过（{status}）"]:
        target(f"{label}: {reason}")


# ---------------------------------------------------------------------------
# PRODUCT_TC_EXECUTED
# ---------------------------------------------------------------------------
def _product_matrix_states(matrix: Any) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for entry in (matrix or {}).get("requirements") or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id") or "")
        if entry_id.startswith("TC-AIQE-"):
            entries[entry_id] = entry
    return entries


def verify_product_tc_executed(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["PRODUCT_TC_EXECUTED"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    config_rel = inputs.option("config", DEFAULT_PRODUCT_CONFIG)
    results_rel = inputs.option("results", DEFAULT_PRODUCT_RESULTS)
    matrix_rel = inputs.option("matrix", DEFAULT_MATRIX)
    coverage_rel = inputs.option("coverage", DEFAULT_COVERAGE)
    expected_commit = (
        str(inputs.item.get("verified_commit_sha") or "").strip()
        or str(inputs.expected_commit or "").strip()
    )

    config = _load_required(inputs, outcome, config_rel, "product-tc-config", kind="yaml")
    results = _load_required(inputs, outcome, results_rel, "product-results", kind="json")
    matrix = _load_required(inputs, outcome, matrix_rel, "requirements matrix", kind="yaml")
    _hash_evidence(inputs, outcome)
    for rel in (config_rel, results_rel, matrix_rel):
        digest = inputs.hash_path(rel)
        if digest:
            outcome.artifact_hashes[str(rel)] = digest
            if str(rel) not in outcome.evidence_refs:
                outcome.evidence_refs.append(str(rel))

    if config is not None:
        _gate_reasons(
            outcome,
            validate_product_config(config, root=inputs.root),
            label="product-tc-config",
        )
        cases = [case for case in config.get("test_cases") or [] if isinstance(case, dict)]
        if len(cases) != len({str(case.get("tc_id")) for case in cases}):
            outcome.conflict("product-tc-config 存在重复 tc_id")
        missing = [tc for tc in TC_IDS if tc not in {str(case.get("tc_id")) for case in cases}]
        if missing:
            outcome.conflict(f"product-tc-config 缺少 TC: {missing}")
        blank_runners: list[str] = []
        for case in cases:
            runner = case.get("runner")
            if runner_is_declared(runner):
                continue
            if runner is None:
                blocked = all(
                    str(case.get(key) or "").strip()
                    for key in ("blocked_by", "owner", "unblock_action")
                )
                if not blocked:
                    blank_runners.append(str(case.get("tc_id")))
            else:
                blank_runners.append(str(case.get("tc_id")))
        if blank_runners:
            outcome.gap(
                "TC runner 为 null/非法且未显式 BLOCKED（blocked_by/owner/unblock_action）: "
                f"{blank_runners}"
            )
        # config 明确未接入 runner 时，结果不得声称该 TC PASS（否则是伪造执行）。
        for case in cases:
            if runner_is_declared(case.get("runner")):
                continue
            tc_id = str(case.get("tc_id"))
            result_status = str(
                next(
                    (
                        item.get("status")
                        for item in (results or {}).get("tests") or []
                        if isinstance(item, dict) and str(item.get("tc_id")) == tc_id
                    ),
                    "",
                )
                or ""
            ).upper()
            if result_status == PASS:
                outcome.conflict(
                    f"{tc_id}: product-tc-config 的 runner 为 null，但 product-results 声称 PASS"
                )
        outcome.checks.append(
            {
                "check": "config_runners",
                "declared": sum(1 for case in cases if runner_is_declared(case.get("runner"))),
                "total": len(cases),
            }
        )

    if config is not None and results is not None:
        expected_environment = str(config.get("environment") or "")
        if not expected_commit:
            outcome.gap("缺少 verified_commit_sha，无法证明产品结果对应当前验收 SHA")
        _gate_reasons(
            outcome,
            validate_product_results(
                results,
                config,
                expected_commit=expected_commit,
                expected_environment=expected_environment,
                root=inputs.root,
                require_verified=True,
                require_baseline=True,
            ),
            label="product-results",
        )

    # ---- 三个来源的状态必须一致；冲突必须显式报错 ----
    matrix_states = _product_matrix_states(matrix) if matrix is not None else {}
    result_states = {
        str(item.get("tc_id")): str(item.get("status") or "").strip().upper()
        for item in (results or {}).get("tests") or []
        if isinstance(item, dict)
    }
    if matrix is not None and results is not None:
        for tc_id in TC_IDS:
            entry = matrix_states.get(tc_id) or {}
            product = ((entry.get("e2e") or {}).get("product") or {})
            matrix_product = str(product.get("status") or "").strip().upper()
            matrix_status = str(entry.get("status") or "").strip().upper()
            result_status = result_states.get(tc_id, "")
            if matrix_product == PASS and matrix_status != PASS:
                outcome.conflict(
                    f"{tc_id}: matrix 自相矛盾（e2e.product.status=PASS 但 requirements.status={matrix_status or '缺失'}）"
                )
            if matrix_product == PASS and result_status != PASS:
                outcome.conflict(
                    f"{tc_id}: matrix 声称产品 PASS，但本次 product-results 状态为 "
                    f"{result_status or '缺失'}"
                )
            if matrix_product and matrix_product != PASS and result_status == PASS:
                outcome.conflict(
                    f"{tc_id}: matrix 产品状态={matrix_product} 与 product-results PASS 矛盾"
                )
            if not matrix_product and not matrix_status:
                outcome.gap(f"{tc_id}: matrix 缺少 e2e.product.status 与 requirements.status")
        matrix_pass = [
            tc
            for tc in TC_IDS
            if str(
                ((matrix_states.get(tc) or {}).get("e2e") or {}).get("product", {}).get("status")
                or ""
            ).upper()
            == PASS
        ]
        result_pass = [tc for tc, status in result_states.items() if status == PASS]
        if len(matrix_pass) != len(result_pass):
            outcome.conflict(
                f"matrix 产品 PASS {len(matrix_pass)} 条与 product-results PASS {len(result_pass)} 条不一致"
            )
        if len(result_pass) == 0 and len(matrix_pass) > 0:
            outcome.conflict("product-results 0 条 PASS，但 matrix/文档声称产品 TC 通过")
        if len(result_pass) != len(TC_IDS):
            outcome.gap(f"产品 TC 本次真实 PASS 仅 {len(result_pass)}/{len(TC_IDS)}")

    if coverage_rel and inputs.path(coverage_rel) is not None and results is not None:
        try:
            coverage_text = inputs.read_text(coverage_rel)
        except RuleExecutionError:
            coverage_text = ""
        if coverage_text:
            outcome.artifact_hashes[str(coverage_rel)] = sha256_file(
                inputs.path(coverage_rel)  # type: ignore[arg-type]
            )
            match = COVERAGE_CLAIM_RE.search(coverage_text)
            result_pass_count = sum(1 for status in result_states.values() if status == PASS)
            if match:
                claimed = int(match.group(1))
                if claimed != result_pass_count:
                    outcome.conflict(
                        f"E2E coverage 声称产品 PASS {claimed}/{match.group(2)}，"
                        f"与 product-results PASS {result_pass_count} 不一致"
                    )
                if claimed and result_pass_count and not _product_results_traceable(results):
                    outcome.conflict(
                        "E2E coverage/product-results 声称产品 TC PASS，但结果缺少 runner/execution/断言/artifact 追溯链"
                    )
    return outcome


def _product_results_traceable(results: Any) -> bool:
    for item in (results or {}).get("tests") or []:
        if not isinstance(item, dict) or str(item.get("status") or "").upper() != PASS:
            continue
        if not runner_is_declared(item.get("runner")):
            return False
        execution = item.get("execution") if isinstance(item.get("execution"), dict) else {}
        if not execution.get("run_id") or not execution.get("job_id"):
            return False
        if not is_sha(execution.get("tested_commit_sha")):
            return False
        if not item.get("assertions") or not item.get("artifacts"):
            return False
    return True


# ---------------------------------------------------------------------------
# RUNTIME_INDEX_CURRENT
# ---------------------------------------------------------------------------
def verify_runtime_index_current(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["RUNTIME_INDEX_CURRENT"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    rel = inputs.option("index", DEFAULT_RUNTIME_INDEX)
    payload = _load_required(inputs, outcome, rel, "evidence-index", kind="json")
    _hash_evidence(inputs, outcome)
    digest = inputs.hash_path(rel)
    if digest:
        outcome.artifact_hashes[str(rel)] = digest
        outcome.evidence_refs.append(str(rel))
    if payload is None:
        return outcome
    expected_commit = (
        str(inputs.item.get("verified_commit_sha") or "").strip()
        or str(inputs.expected_commit or "").strip()
    )
    require_tcs = int(inputs.option("require_tcs", 10) or 0)
    _gate_reasons(
        outcome,
        validate_runtime_index(
            payload,
            expected_commit=expected_commit or None,
            allow_local=False,
            require_platform_tcs=require_tcs,
        ),
        label="runtime-index",
    )
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    workflow = payload.get("workflow") if isinstance(payload.get("workflow"), dict) else {}
    verification = payload.get("verification") if isinstance(payload.get("verification"), dict) else {}
    artifacts = payload.get("artifacts")
    for block, value in (
        ("source", source),
        ("runtime", runtime),
        ("workflow", workflow),
        ("verification", verification),
    ):
        if not isinstance(value, dict) or not value:
            outcome.gap(f"evidence-index 缺少 FIX-011 provenance 区块: {block}")
    if not isinstance(artifacts, list) or not artifacts:
        outcome.gap("evidence-index 缺少 artifacts 清单（name/path/sha256/job_id）")
    else:
        for index, artifact in enumerate(artifacts, 1):
            if not isinstance(artifact, dict):
                outcome.conflict(f"evidence-index artifacts[{index}] 不是对象")
                continue
            missing = [
                key for key in ("name", "sha256", "job_id") if not artifact.get(key)
            ]
            if missing:
                outcome.gap(f"evidence-index artifacts[{index}] 缺少字段 {missing}")
    tested = str(source.get("tested_commit_sha") or "").strip().lower()
    commit = str(payload.get("commit_sha") or "").strip().lower()
    if tested and commit and tested != commit:
        outcome.conflict(
            f"evidence-index commit_sha={commit[:12]} 与 source.tested_commit_sha={tested[:12]} 不一致"
        )
    environment = str(payload.get("environment") or "").strip()
    runtime_environment = str(runtime.get("environment") or "").strip()
    if runtime_environment and environment and runtime_environment != environment:
        outcome.conflict(
            f"evidence-index environment={environment!r} 与 runtime.environment={runtime_environment!r} 不一致"
        )
    if environment and environment.lower().startswith(("local", "dev")):
        outcome.conflict(
            f"evidence-index environment={environment!r} 为本地/开发环境，不能作为 GA 运行时证据"
        )
    ci_run_id = str(payload.get("ci_run_id") or "").strip()
    if ci_run_id.lower().startswith(("local", "none", "0")):
        outcome.conflict(
            f"evidence-index ci_run_id={ci_run_id!r} 不是真实 CI 执行身份，不能作为运行证据"
        )
    if verification.get("errors"):
        outcome.conflict(f"evidence-index verification.errors 非空: {verification.get('errors')}")
    if verification.get("provenance_valid") is not True:
        outcome.gap("evidence-index verification.provenance_valid 不为 true")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("provenance_valid") is False:
        outcome.gap("evidence-index summary.provenance_valid 为 false")
    return outcome


# ---------------------------------------------------------------------------
# PROVENANCE_CONSISTENT
# ---------------------------------------------------------------------------
def _parse_down_revision(text: str) -> str | tuple[str, ...] | None:
    match = re.search(r"^down_revision(?::\s*[^=]+)?\s*=\s*(.+)$", text, re.MULTILINE)
    if not match:
        return None
    remainder = match.group(1)
    offset = match.end()
    while remainder.count("(") > remainder.count(")") and offset < len(text):
        newline = text.find("\n", offset)
        if newline == -1:
            break
        tail = text[newline + 1 :].splitlines()
        line = tail[0] if tail else ""
        remainder += " " + line
        offset = newline + 1 + len(line)
    names = re.findall(r"['\"]([^'\"]+)['\"]", remainder)
    if not names:
        return None
    if len(names) == 1 and "(" not in remainder:
        return names[0]
    return tuple(names)


def _alembic_heads(versions_dir: Path) -> tuple[str | None, int]:
    """从 alembic 迁移文件推导 head（revision - down_revision，含 merge 多父）。"""
    revisions: dict[str, str | tuple[str, ...] | None] = {}
    referenced: set[str] = set()
    for path in sorted(versions_dir.glob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        revision = re.search(
            r"^revision(?:\s*:\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE
        )
        if not revision:
            continue
        down = _parse_down_revision(text)
        revisions[revision.group(1)] = down
        if isinstance(down, str):
            referenced.add(down)
        elif isinstance(down, tuple):
            referenced.update(down)
    heads = sorted(revision for revision in revisions if revision not in referenced)
    if len(heads) == 1:
        return heads[0], 1
    return (heads[0] if heads else None), len(heads)


def _fingerprint_checks(inputs: RuleInputs, outcome: RuleOutcome) -> None:
    """校验 baseline SHA / migration head / release verdict 指纹一致。"""
    matrix_rel = inputs.option("matrix")
    if not matrix_rel:
        return
    try:
        matrix = inputs.read_yaml(matrix_rel)
    except RuleExecutionError as exc:
        outcome.gap(f"requirements matrix: {exc}")
        return
    if not isinstance(matrix, dict):
        outcome.conflict("requirements matrix 不是对象")
        return
    digest = inputs.hash_path(matrix_rel)
    if digest:
        outcome.artifact_hashes[str(matrix_rel)] = digest
        outcome.evidence_refs.append(str(matrix_rel))
    baseline = matrix.get("baseline") if isinstance(matrix.get("baseline"), dict) else {}
    release_commit = str(baseline.get("release_commit") or "").strip().lower()
    migration_head = str(baseline.get("migration_head") or "").strip()
    if not is_sha(release_commit):
        outcome.conflict("requirements matrix 缺少合法 baseline.release_commit（40 位 SHA）")
    if not migration_head:
        outcome.conflict("requirements matrix 缺少 baseline.migration_head")
    versions_rel = inputs.option("alembic_versions")
    if versions_rel:
        versions_dir = inputs.path(versions_rel)
        if versions_dir is None or not versions_dir.is_dir():
            outcome.gap(f"alembic versions 目录不存在或越界: {versions_rel!r}")
        else:
            head, head_count = _alembic_heads(versions_dir)
            if head_count != 1:
                outcome.conflict(f"Alembic 存在 {head_count} 个 head（必须单头）")
            elif migration_head and head and migration_head != head:
                outcome.conflict(
                    f"matrix migration_head={migration_head!r} 与实际 Alembic head {head!r} 不一致"
                )
    verdict_rel = inputs.option("release_verdict")
    if verdict_rel and inputs.path(verdict_rel) is not None:
        try:
            verdict = inputs.read_json(verdict_rel)
        except RuleExecutionError as exc:
            outcome.gap(f"release-verdict: {exc}")
            verdict = None
        if isinstance(verdict, dict):
            digest = inputs.hash_path(verdict_rel)
            if digest:
                outcome.artifact_hashes[str(verdict_rel)] = digest
                outcome.evidence_refs.append(str(verdict_rel))
            verdict_baseline = str(verdict.get("baseline_release_commit") or "").strip().lower()
            if release_commit and verdict_baseline and release_commit != verdict_baseline:
                outcome.conflict(
                    f"matrix baseline={release_commit[:12]} 与 release-verdict "
                    f"baseline_release_commit={verdict_baseline[:12]} 不一致"
                )
            verdict_head = str(verdict.get("migration_head") or "").strip()
            if migration_head and verdict_head and migration_head != verdict_head:
                outcome.conflict(
                    f"matrix migration_head={migration_head!r} 与 release-verdict "
                    f"migration_head={verdict_head!r} 不一致"
                )


def verify_provenance_consistent(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["PROVENANCE_CONSISTENT"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    payload_rel = inputs.option("payload", DEFAULT_RUNTIME_INDEX)
    platform_rel = inputs.option("platform_results", DEFAULT_PLATFORM_RESULTS)
    expected_commit = (
        str(inputs.item.get("verified_commit_sha") or "").strip()
        or str(inputs.expected_commit or "").strip()
    )
    _fingerprint_checks(inputs, outcome)
    if payload_rel is None:
        _hash_evidence(inputs, outcome)
        if not outcome.reasons:
            outcome.gap("PROVENANCE_CONSISTENT 没有可校验的 provenance 输入")
        return outcome
    payload = _load_required(inputs, outcome, payload_rel, "provenance payload", kind="json")
    _hash_evidence(inputs, outcome)
    for path_rel in (payload_rel, platform_rel):
        digest = inputs.hash_path(path_rel)
        if digest:
            outcome.artifact_hashes[str(path_rel)] = digest
            outcome.evidence_refs.append(str(path_rel))
    if payload is None:
        return outcome
    _gate_reasons(
        outcome,
        validate_provenance(
            payload,
            expected_tested_sha=expected_commit,
            root=inputs.root,
            require_pr_head=bool(inputs.option("require_pr_head", False)),
            require_container_digest=bool(inputs.option("require_container_digest", False)),
        ),
        label="provenance",
    )
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    environment = str(runtime.get("environment") or payload.get("environment") or "").strip()
    if environment and environment.lower().startswith(("local", "dev")):
        outcome.conflict(
            f"environment={environment!r} 为本地/开发环境，不能作为 GA provenance"
        )
    platform_path = inputs.path(platform_rel) if platform_rel else None
    if platform_path is not None and platform_path.is_file():
        try:
            platform = inputs.read_json(platform_rel)
        except RuleExecutionError as exc:
            outcome.gap(f"platform-results: {exc}")
            platform = None
        if isinstance(platform, dict):
            index_commit = str(payload.get("commit_sha") or "").strip().lower()
            platform_commit = str(platform.get("commit_sha") or "").strip().lower()
            if index_commit and platform_commit and index_commit != platform_commit:
                outcome.conflict(
                    f"evidence-index commit_sha={index_commit[:12]} 与 platform-results "
                    f"commit_sha={platform_commit[:12]} 不一致"
                )
            index_environment = str(payload.get("environment") or "").strip()
            platform_environment = str(platform.get("environment") or "").strip()
            if index_environment and platform_environment and index_environment != platform_environment:
                outcome.conflict(
                    f"evidence-index environment={index_environment!r} 与 platform-results "
                    f"environment={platform_environment!r} 不一致（Builder 不得替换环境）"
                )
            platform_ci_run = str(platform.get("ci_run") or platform.get("ci_run_id") or "").strip()
            workflow = payload.get("workflow") if isinstance(payload.get("workflow"), dict) else {}
            index_ci_run = str(workflow.get("run_id") or payload.get("ci_run_id") or "").strip()
            if platform_ci_run and index_ci_run and platform_ci_run != index_ci_run:
                outcome.conflict(
                    f"evidence-index workflow.run_id={index_ci_run!r} 与 platform-results "
                    f"ci_run={platform_ci_run!r} 不一致"
                )
    return outcome


# ---------------------------------------------------------------------------
# SECRET_SCAN_CURRENT
# ---------------------------------------------------------------------------
def _scan_count(summary: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in summary and summary.get(key) is not None:
            try:
                return int(summary.get(key))
            except (TypeError, ValueError):
                return None
    return None


def _weak_default_explained(payload: dict[str, Any]) -> bool:
    for key in ("weak_default_explanation", "weak_defaults_explanation", "weak_default_reason"):
        if str(payload.get(key) or "").strip():
            return True
    findings = payload.get("findings") or []
    weak = [
        finding
        for finding in findings
        if isinstance(finding, dict)
        and str(finding.get("classification") or "").lower() in {"weak-default", "weak_default"}
    ]
    if not weak:
        return False
    return all(
        any(str(finding.get(key) or "").strip() for key in ("rationale", "justification", "explanation"))
        for finding in weak
    )


def verify_secret_scan_current(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["SECRET_SCAN_CURRENT"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    rel = inputs.option("scan", DEFAULT_CREDENTIAL_SCAN)
    payload = _load_required(inputs, outcome, rel, "credential-scan", kind="json")
    _hash_evidence(inputs, outcome)
    digest = inputs.hash_path(rel)
    if digest:
        outcome.artifact_hashes[str(rel)] = digest
        outcome.evidence_refs.append(str(rel))
    if payload is None:
        return outcome
    if not isinstance(payload, dict):
        outcome.conflict("credential-scan 不是对象")
        return outcome
    scan_sha = str(
        payload.get("scan_commit_sha")
        or payload.get("commit_sha")
        or payload.get("source_commit_sha")
        or ""
    ).strip().lower()
    expected_commit = (
        str(inputs.item.get("verified_commit_sha") or "").strip().lower()
        or str(inputs.expected_commit or "").strip().lower()
    )
    if not is_sha(scan_sha):
        outcome.conflict(
            "credential-scan 缺少 40 位 scan_commit_sha，旧扫描结果不能当作当前证据"
        )
    elif expected_commit and scan_sha != expected_commit:
        outcome.conflict(
            f"credential-scan scan_commit_sha={scan_sha[:12]} 不是当前验收 SHA "
            f"{expected_commit[:12]}，扫描结果已过期"
        )
    if parse_time(payload.get("generated_at")) is None:
        outcome.conflict("credential-scan 缺少可解析的 generated_at")
    status = str(payload.get("status") or "").strip().upper()
    if status and status not in {"CLEAN", "PASS"}:
        outcome.conflict(f"credential-scan status={status}，不能作为 CLEAN 证据")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    potential = _scan_count(summary, "potential_secret", "potential_secret_count", "potential_secrets")
    if potential is None:
        outcome.gap("credential-scan summary 缺少 potential_secret 计数")
    elif potential != 0:
        outcome.conflict(f"credential-scan potential_secret={potential}，必须先复核并轮换")
    weak = _scan_count(summary, "weak_default", "weak_default_count")
    if weak is None:
        outcome.gap("credential-scan summary 缺少 weak_default 计数")
    elif weak > 0 and not _weak_default_explained(payload):
        outcome.conflict(
            f"credential-scan weak_default={weak} 未解释（需 weak_default_explanation 或逐条 rationale）"
        )
    history = payload.get("history_summary") if isinstance(payload.get("history_summary"), dict) else {}
    history_potential = _scan_count(history, "potential_secret", "potential_secret_count")
    if history_potential:
        outcome.conflict(f"credential-scan 历史提交仍有 potential_secret={history_potential}")
    return outcome


# ---------------------------------------------------------------------------
# BRANCH_RULESET_REQUIRED_CHECKS
# ---------------------------------------------------------------------------
def verify_branch_ruleset(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["BRANCH_RULESET_REQUIRED_CHECKS"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    rel = inputs.option("branch_protection", DEFAULT_BRANCH_PROTECTION)
    payload = _load_required(inputs, outcome, rel, "branch-protection", kind="json")
    _hash_evidence(inputs, outcome)
    digest = inputs.hash_path(rel)
    if digest:
        outcome.artifact_hashes[str(rel)] = digest
        outcome.evidence_refs.append(str(rel))
    if payload is None:
        return outcome
    if not isinstance(payload, dict):
        outcome.conflict("branch-protection 不是对象")
        return outcome
    names = {str(item) for item in payload.get("required_checks") or []}
    for ruleset in payload.get("rulesets") or []:
        for rule_entry in (ruleset or {}).get("rules") or []:
            if not isinstance(rule_entry, dict) or rule_entry.get("type") != "required_status_checks":
                continue
            for check in (rule_entry.get("parameters") or {}).get("required_status_checks") or []:
                context = str((check or {}).get("context") or "").strip()
                if context:
                    names.add(context)
    if AIQE_AGGREGATE_CHECK not in names:
        outcome.conflict(
            f"Main Ruleset 未要求 AIQE 聚合 Gate {AIQE_AGGREGATE_CHECK!r}；"
            "规则未实际更新前该审计项不得 CLOSED"
        )
    _gate_reasons(outcome, validate_branch_protection(payload), label="branch-protection")
    outcome.checks.append({"check": "required_checks", "contexts": sorted(names)})
    return outcome


# ---------------------------------------------------------------------------
# TEST_EVIDENCE
# ---------------------------------------------------------------------------
def _test_symbols(tree: ast.Module) -> set[str]:
    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.add(f"{node.name}::{child.name}")
    return symbols


def verify_test_evidence(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["TEST_EVIDENCE"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    test_ids = inputs.option("test_ids") or []
    if not isinstance(test_ids, list) or not test_ids:
        outcome.gap("TEST_EVIDENCE 必须给出可执行测试 ID（pytest node id），不能只判断路径存在")
        _hash_evidence(inputs, outcome)
        return outcome
    for raw in test_ids:
        test_id = str(raw or "").strip()
        if not test_id:
            outcome.gap("test_ids 含空条目")
            continue
        parts = test_id.split("::")
        rel = parts[0].strip()
        symbol = "::".join(parts[1:]).strip()
        path = inputs.path(rel)
        if path is None or not path.is_file():
            outcome.conflict(f"测试文件不存在或越界: {rel}")
            continue
        outcome.artifact_hashes[rel] = sha256_file(path)
        if rel not in outcome.evidence_refs:
            outcome.evidence_refs.append(rel)
        if not symbol:
            outcome.gap(f"{test_id}: 只给了文件，没有 pytest 用例 ID")
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as exc:
            outcome.conflict(f"{rel} 无法解析: {exc}")
            continue
        symbols = _test_symbols(tree)
        if symbol not in symbols:
            outcome.conflict(f"{test_id}: 测试用例不存在（AST 未找到 {symbol}）")
        elif not symbol.split("::")[-1].startswith("test"):
            outcome.gap(f"{test_id}: 符号 {symbol} 不是 pytest 用例")
        else:
            outcome.checks.append({"test_id": test_id, "resolved": True})
    expected_hashes = inputs.option("evidence_hashes") or {}
    if isinstance(expected_hashes, dict):
        for rel, expected in expected_hashes.items():
            digest = inputs.hash_path(rel)
            if digest is None:
                outcome.conflict(f"evidence_hashes 指向的文件不存在: {rel}")
            elif str(expected).lower().removeprefix("sha256:") != digest:
                outcome.conflict(f"evidence_hashes 中 {rel} 的 sha256 与当前文件不一致")
    _hash_evidence(inputs, outcome)
    return outcome


# ---------------------------------------------------------------------------
# DOC_SEMANTICS / GENERIC_FILE_EVIDENCE
# ---------------------------------------------------------------------------
def verify_doc_semantics(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["DOC_SEMANTICS"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    assertions = inputs.option("assertions")
    executed = _verify_assertions(inputs, outcome, assertions)
    if not assertions:
        outcome.gap("DOC_SEMANTICS 必须给出文档语义断言（must_contain / pointer 等）")
    elif executed == 0:
        outcome.gap("DOC_SEMANTICS 没有可执行的内容断言")
    _hash_evidence(inputs, outcome)
    return outcome


def verify_generic_file_evidence(inputs: RuleInputs) -> RuleOutcome:
    rule = RULES["GENERIC_FILE_EVIDENCE"]
    outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
    assertions = inputs.option("assertions")
    executed = _verify_assertions(inputs, outcome, assertions)
    if not assertions:
        outcome.gap(
            "GENERIC_FILE_EVIDENCE 只允许用于确实只能验证文件/测试存在的条目，"
            "且必须给出路径 + 内容断言 + hash"
        )
        for rel in _evidence_paths(inputs):
            if not inputs.hash_path(rel):
                outcome.conflict(f"证据不存在或越界: {rel}")
    elif executed == 0:
        outcome.gap("GENERIC_FILE_EVIDENCE 没有可执行的内容断言（不能只判断路径存在）")
    _hash_evidence(inputs, outcome)
    return outcome


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------
register(
    ClosureRule(
        rule_id="PRODUCT_TC_EXECUTED",
        description="产品 TC 10/10 必须由本次真实 Runner 执行（runner/execution/断言/artifact/SHA），"
        "并与 requirements matrix 的 e2e.product.status 一致；PASS/PARTIAL/0-of-10 冲突直接报错。",
        verifier_name="product_tc_closure_verifier",
        verifier_version="1.0.0",
        func=verify_product_tc_executed,
    )
)
register(
    ClosureRule(
        rule_id="RUNTIME_INDEX_CURRENT",
        description="evidence-index.json 的 commit_sha/环境/ga_ready/summary 必须与逐条记录一致，"
        "且包含 FIX-011 的 source/runtime/workflow/artifacts/verification provenance。",
        verifier_name="runtime_index_closure_verifier",
        verifier_version="1.0.0",
        func=verify_runtime_index_current,
    )
)
register(
    ClosureRule(
        rule_id="PROVENANCE_CONSISTENT",
        description="调用 validators.provenance.validate_provenance 校验 tested/head/merge/release SHA、"
        "环境、起止时间与 artifact hash；并交叉核对 requirements baseline SHA、migration head、"
        "release-verdict 与 evidence-index/platform-results 的 commit/环境/CI Run。",
        verifier_name="provenance_closure_verifier",
        verifier_version="1.0.0",
        func=verify_provenance_consistent,
    )
)
register(
    ClosureRule(
        rule_id="SECRET_SCAN_CURRENT",
        description="credential-scan.json 必须是当前 SHA 的 40 位 scan_commit_sha + generated_at，"
        "potential_secret=0 且 weak_default 有解释；旧扫描结果不能当当前证据。",
        verifier_name="credential_scan_closure_verifier",
        verifier_version="1.0.0",
        func=verify_secret_scan_current,
    )
)
register(
    ClosureRule(
        rule_id="BRANCH_RULESET_REQUIRED_CHECKS",
        description="调用 validators.branch.validate_branch_protection，Main Ruleset 必须精确包含 "
        f"{AIQE_AGGREGATE_CHECK!r} 与其余 required checks。",
        verifier_name="branch_ruleset_closure_verifier",
        verifier_version="1.0.0",
        func=verify_branch_ruleset,
    )
)
register(
    ClosureRule(
        rule_id="TEST_EVIDENCE",
        description="仅用于确实只能验证测试存在的条目：必须给出 pytest 用例 ID（AST 解析确认存在）"
        "与证据文件 hash，并需要真实 verified_commit_sha。",
        verifier_name="test_evidence_closure_verifier",
        verifier_version="1.0.0",
        func=verify_test_evidence,
    )
)
register(
    ClosureRule(
        rule_id="DOC_SEMANTICS",
        description="仅用于只能验证文档语义的条目：断言必须包含文档关键内容/YAML/JSON 字段，"
        "不能只判断路径存在；需要 verified_commit_sha 与证据 hash。",
        verifier_name="doc_semantics_closure_verifier",
        verifier_version="1.0.0",
        func=verify_doc_semantics,
    )
)
register(
    ClosureRule(
        rule_id="GENERIC_FILE_EVIDENCE",
        description="兜底规则：只允许用于确实只能验证文件存在的条目，且必须同时给出内容断言、"
        "证据 hash 与可执行 verifier 名称/版本，否则不得 CLOSED。",
        verifier_name="generic_file_evidence_closure_verifier",
        verifier_version="1.0.0",
        func=verify_generic_file_evidence,
    )
)


def verify_item(
    item: dict[str, Any],
    *,
    root: Path,
    expected_commit: str = "",
) -> RuleOutcome:
    """执行单个审计条目的关闭规则；异常一律降级为 NOT_PROVEN，绝不 PASS。"""
    rule_id = str(item.get("closure_rule_id") or "").strip()
    rule = get_rule(rule_id)
    if rule is None:
        outcome = RuleOutcome(rule_id or "<missing>", "<unregistered>", "<unregistered>")
        outcome.gap(f"closure_rule_id 未注册: {rule_id!r}")
        return outcome
    inputs = RuleInputs(root=Path(root), item=item, expected_commit=expected_commit)
    try:
        outcome = rule.verify(inputs)
    except RuleExecutionError as exc:
        outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
        outcome.gap(f"规则执行失败: {exc}")
    except Exception as exc:  # pragma: no cover - 防御：规则 bug 不得变成 PASS
        outcome = RuleOutcome(rule.rule_id, rule.verifier_name, rule.verifier_version)
        outcome.gap(f"规则执行异常: {type(exc).__name__}: {exc}")
    if outcome.rule_id != rule.rule_id:
        outcome.rule_id = rule.rule_id
    if outcome.verifier_name != rule.verifier_name:
        outcome.verifier_name = rule.verifier_name
    if outcome.verifier_version != rule.verifier_version:
        outcome.verifier_version = rule.verifier_version
    return outcome


__all__ = [
    "ClosureRule",
    "RuleExecutionError",
    "RuleInputs",
    "RuleOutcome",
    "get_rule",
    "register",
    "rule_ids",
    "verify_item",
]
