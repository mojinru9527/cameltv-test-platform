"""产品级 TC Runner 统一合同与结果写出（V1.6.2 FIX-002 / FIX-003）。

单一事实源
----------
本模块是 ``product-tc-config.yaml``（schema 2.0）与 ``product-results.json``
（``artifact_kind=product-tc-results``）的唯一合同实现：

- 配置：每条 TC 必须声明 ``title`` / ``spec_ref`` / ``baseline_version`` /
  ``required_environment`` / ``required_assertions`` / ``required_artifacts`` /
  ``timeout_seconds``；``runner: null`` 必须同时给出
  ``blocked_by`` / ``owner`` / ``unblock_action`` / ``blocked_status=BLOCKED``。
- 结果：``PASS`` 必须同时具备
  ``runner{name,type,version,entrypoint}``、
  ``execution{run_id|execution_id,job_id,tested_commit_sha,environment,started_at,finished_at,duration_ms}``、
  ``assertions[{assertion_id,status,evidence_ref}]`` 与
  ``artifacts[{artifact_id,kind,path,sha256}]``。缺任何一项都只能是
  ``FAIL`` / ``NOT_PROVEN``，绝不允许由本模块或调用方补造字段后升级为 PASS。
- 禁止：旧格式 PASS 记录、半自动/截图结果、外部生产手工脚本、没有真实
  Run/Job/断言/artifact 的摘要，都不能折算为 PASS。

runner 脚本约定
----------------
``run_product_tc.py --run`` 调用 runner 时注入以下环境变量：

- ``AIQE_TC_RESULT_PATH``：runner 必须把机器结果 JSON 写到该路径；
- ``AIQE_TC_ID``：本次 TC ID；
- ``AIQE_TC_ROOT``：artifact 路径解析根目录（仓库根或测试 fixture 根）；
- ``AIQE_TESTED_COMMIT_SHA``：本次实际 checkout / 测试 SHA；
- ``AIQE_TC_ENVIRONMENT``：本次目标环境；
- ``AIQE_AIQE_SCRIPTS_DIR``：``scripts/aiqe`` 绝对路径，便于
  ``sys.path.insert(0, ...)`` 后 ``from per_tc.runner_contract import ...``。

runner 必须从正式入口执行（REST API / Worker / 外部 Runner），不得 Service 直调。
"""
from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AIQE_DIR = Path(__file__).resolve().parents[1]
if str(AIQE_DIR) not in sys.path:
    sys.path.insert(0, str(AIQE_DIR))

from statuses import (  # noqa: E402
    BLOCKED,
    FAIL,
    NOT_PROVEN,
    NOT_RUN,
    PARTIAL,
    PASS,
    STATUSES,
    UNKNOWN,
    WAIVED,
)
from validators.common import (  # noqa: E402
    duration_ms,
    is_sha,
    is_sha256,
    resolve_repo_path,
    sha256_file,
)

CONFIG_SCHEMA_VERSION = "2.0"
SCHEMA_VERSION = "2.0"
ARTIFACT_KIND = "product-tc-results"
VERIFIER_NAME = "verify_product_tc_results"
VERIFIER_VERSION = "1.0.0"
TC_IDS = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))
RUNNER_TYPES = frozenset(
    {"api_worker_e2e", "api_e2e", "ui_e2e", "external_runner", "db_readonly", "benchmark_e2e"}
)
ALLOWED_ENVIRONMENTS = frozenset({"isolated-test", "staging-test", "ci-test"})
MANDATORY_CASE_FIELDS_V2 = (
    "title",
    "spec_ref",
    "baseline_version",
    "required_environment",
    "required_assertions",
    "required_artifacts",
    "timeout_seconds",
)
MANDATORY_BLOCKED_FIELDS = ("blocked_by", "owner", "unblock_action")
PYTHON_ALIASES = frozenset({"python", "python3", "python.exe", "py", "py.exe"})
TIME_TOLERANCE_MIN_MS = 2000
TIME_TOLERANCE_RATIO = 0.1
_NON_PASS_STATUSES = (FAIL, BLOCKED, NOT_RUN, NOT_PROVEN, PARTIAL, WAIVED, UNKNOWN)
_REASON_FIELDS = ("blocked_reason", "reason", "failure_reason")


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return now_utc().isoformat(timespec="milliseconds")


def environment_errors(environment: object) -> list[str]:
    """产品 TC 只能跑在受控隔离/CI/staging 环境；local 与 production 一律拒绝。"""
    text = str(environment or "").strip()
    if not text:
        return ["environment 不能为空"]
    if text.lower() not in ALLOWED_ENVIRONMENTS:
        allowed = ", ".join(sorted(ALLOWED_ENVIRONMENTS))
        return [
            f"environment={text!r} 不在允许集合 [{allowed}]；"
            "local / localhost / production 不能作为产品 TC 验收环境"
        ]
    return []


def config_schema_is_v2(config: Mapping[str, Any] | None) -> bool:
    return str((config or {}).get("schema_version") or "").strip() == CONFIG_SCHEMA_VERSION


def runner_entrypoint(runner: object) -> str:
    if isinstance(runner, Mapping):
        return str(runner.get("entrypoint") or "").strip()
    if isinstance(runner, list) and runner:
        items = [str(item) for item in runner]
        if len(items) > 1 and Path(items[0]).name.lower() in PYTHON_ALIASES:
            return items[1]
        return items[0]
    return ""


def runner_argv(runner: object) -> list[str] | None:
    """把配置里的 runner 声明转换为可执行的 argv；不可执行时返回 None。"""
    if isinstance(runner, Mapping):
        entrypoint = str(runner.get("entrypoint") or "").strip()
        if not entrypoint:
            return None
        arguments = runner.get("args") or []
        args = [str(item) for item in arguments] if isinstance(arguments, list) else []
        if entrypoint.lower().endswith(".py"):
            return [sys.executable, entrypoint, *args]
        return [entrypoint, *args]
    if isinstance(runner, list) and runner:
        items = [str(item) for item in runner]
        if len(items) > 1 and Path(items[0]).name.lower() in PYTHON_ALIASES:
            return [sys.executable, *items[1:]]
        return items
    return None


def runner_metadata(runner: object, *, name: str = "") -> dict[str, Any]:
    """结果记录里的 runner 元数据；空 runner 明确标为 unregistered，不伪造执行器。"""
    entrypoint = runner_entrypoint(runner)
    fallback_name = Path(entrypoint).stem if entrypoint else (name or "unregistered")
    if isinstance(runner, Mapping):
        return {
            "name": str(runner.get("name") or fallback_name),
            "type": str(runner.get("type") or "external_runner"),
            "version": str(runner.get("version") or "0.0.0"),
            "entrypoint": entrypoint or None,
        }
    if isinstance(runner, list) and runner:
        return {
            "name": fallback_name,
            "type": "external_runner",
            "version": "unknown",
            "entrypoint": entrypoint or None,
        }
    return {"name": fallback_name, "type": "none", "version": "0.0.0", "entrypoint": None}


def runner_is_declared(runner: object) -> bool:
    if not isinstance(runner, Mapping):
        return False
    return all(
        str(runner.get(key) or "").strip() for key in ("name", "type", "version", "entrypoint")
    )


def _runner_argv_errors(runner: list[Any], tc_id: str, root: Path) -> list[str]:
    items = [str(item) for item in runner]
    if not items:
        return [f"{tc_id}: runner 不能为空列表"]
    if len(items) > 1 and Path(items[0]).name.lower() in PYTHON_ALIASES:
        script = items[1]
    else:
        script = items[0]
    path = resolve_repo_path(root, script)
    if path is None or not path.is_file():
        return [f"{tc_id}: runner 脚本不存在或越界: {script}"]
    return []


def _validate_case_v2(
    case: Mapping[str, Any], tc_id: str, baseline: str, errors: list[str]
) -> None:
    case_baseline = str(case.get("baseline_version") or "").strip()
    if not case_baseline:
        errors.append(f"{tc_id}: 缺少 baseline_version")
    elif baseline and case_baseline != baseline:
        errors.append(f"{tc_id}: baseline_version={case_baseline} 与全局 {baseline} 不一致")
    required_environment = str(case.get("required_environment") or "").strip()
    if not required_environment:
        errors.append(f"{tc_id}: 缺少 required_environment")
    else:
        errors.extend(f"{tc_id}: {item}" for item in environment_errors(required_environment))
    for field in ("required_assertions", "required_artifacts"):
        value = case.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{tc_id}: {field} 必须是非空列表")
            continue
        if any(not str(item or "").strip() for item in value):
            errors.append(f"{tc_id}: {field} 含空值")
    timeout = case.get("timeout_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        errors.append(f"{tc_id}: timeout_seconds 必须是正整数")


def _validate_runner(
    case: Mapping[str, Any], tc_id: str, root: Path, strict: bool, errors: list[str]
) -> None:
    runner = case.get("runner")
    if runner is None:
        if not str(case.get("blocked_by") or "").strip():
            errors.append(f"{tc_id}: runner 为空时必须显式填写 blocked_by")
        if strict:
            for field in ("owner", "unblock_action"):
                if not str(case.get(field) or "").strip():
                    errors.append(f"{tc_id}: runner 为空时必须显式填写 {field}")
            blocked_status = str(case.get("blocked_status") or "").strip().upper()
            if blocked_status != BLOCKED:
                errors.append(f"{tc_id}: runner 为空时 blocked_status 必须是 BLOCKED")
        return
    if isinstance(runner, list):
        errors.extend(_runner_argv_errors(runner, tc_id, root))
        return
    if isinstance(runner, Mapping):
        runner_type = str(runner.get("type") or "").strip()
        if not runner_type:
            errors.append(f"{tc_id}: runner 缺少 type")
        elif runner_type not in RUNNER_TYPES:
            errors.append(f"{tc_id}: 未注册的 runner.type {runner_type!r}")
        if not str(runner.get("version") or "").strip():
            errors.append(f"{tc_id}: runner 缺少 version")
        entrypoint = str(runner.get("entrypoint") or "").strip()
        if not entrypoint:
            errors.append(f"{tc_id}: runner 缺少 entrypoint")
        else:
            path = resolve_repo_path(root, entrypoint)
            if path is None or not path.is_file():
                errors.append(f"{tc_id}: runner 入口不存在或越界: {entrypoint}")
        arguments = runner.get("args")
        if arguments is not None and (
            not isinstance(arguments, list) or any(not isinstance(item, str) for item in arguments)
        ):
            errors.append(f"{tc_id}: runner.args 必须是字符串列表")
        return
    errors.append(f"{tc_id}: runner 结构非法: {runner!r}")


def validate_config(config: object, *, root: Path) -> list[str]:
    """校验 product-tc-config.yaml；schema 2.0 启用全部新字段语义。

    旧 schema（local rehearsal 配置）按兼容模式校验，但永远不会因此获得 PASS。
    """
    errors: list[str] = []
    if not isinstance(config, Mapping) or not config:
        return ["product-tc-config 为空或不是对象"]
    schema = str(config.get("schema_version") or "").strip()
    strict = schema == CONFIG_SCHEMA_VERSION
    environment = str(config.get("environment") or "").strip()
    baseline = str(config.get("baseline_version") or "").strip()
    if strict:
        if not baseline:
            errors.append("product-tc-config 缺少 baseline_version")
        errors.extend(environment_errors(environment))
    elif not environment:
        errors.append("product-tc-config 缺少 environment")
    cases = config.get("test_cases")
    if not isinstance(cases, list) or not cases:
        errors.append("test_cases 必须是非空列表")
        return errors
    ids: list[str] = []
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            errors.append(f"test_cases[{index}] 不是对象")
            continue
        tc_id = str(case.get("tc_id") or f"#{index}").strip()
        ids.append(tc_id)
        if tc_id not in TC_IDS:
            errors.append(f"未批准的产品 TC: {tc_id}")
        if not str(case.get("title") or "").strip():
            errors.append(f"{tc_id}: 缺少 title")
        if not str(case.get("spec_ref") or "").strip():
            errors.append(f"{tc_id}: 缺少 spec_ref")
        if strict:
            _validate_case_v2(case, tc_id, baseline, errors)
        _validate_runner(case, tc_id, root, strict, errors)
        evidence_glob = case.get("evidence_glob")
        if evidence_glob is not None and not str(evidence_glob).strip():
            errors.append(f"{tc_id}: evidence_glob 不能为空字符串")
    for tc_id in TC_IDS:
        if tc_id not in ids:
            errors.append(f"缺少产品 TC: {tc_id}")
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    for tc_id in duplicates:
        errors.append(f"重复 tc_id: {tc_id}")
    return errors


def execution_block(
    *,
    run_id: str = "",
    execution_id: str = "",
    job_id: str = "",
    tested_commit_sha: str = "",
    environment: str = "",
    started_at: str | datetime = "",
    finished_at: str | datetime = "",
    reported_duration_ms: int | None = None,
) -> dict[str, Any]:
    """构造 execution 块；duration_ms 默认由起止时间计算，不接受 0。"""
    started = started_at.isoformat(timespec="milliseconds") if isinstance(started_at, datetime) else str(started_at)
    finished = finished_at.isoformat(timespec="milliseconds") if isinstance(finished_at, datetime) else str(finished_at)
    measured = duration_ms(started, finished)
    duration = int(reported_duration_ms) if reported_duration_ms is not None else int(measured or 0)
    block: dict[str, Any] = {
        "run_id": str(run_id or ""),
        "job_id": str(job_id or ""),
        "tested_commit_sha": str(tested_commit_sha or "").strip().lower(),
        "environment": str(environment or "").strip(),
        "started_at": started,
        "finished_at": finished,
        "duration_ms": duration,
    }
    if execution_id:
        block["execution_id"] = str(execution_id)
    return block


def assertion_result(
    assertion_id: str, *, status: str = PASS, evidence_ref: str = ""
) -> dict[str, Any]:
    return {
        "assertion_id": str(assertion_id),
        "status": str(status).upper(),
        "evidence_ref": str(evidence_ref),
    }


def artifact_entry(artifact_id: str, kind: str, path: str, *, root: Path) -> dict[str, Any]:
    """生成 artifact 条目并计算真实 sha256；路径必须位于 root 内且文件存在。"""
    resolved = resolve_repo_path(root, path)
    if resolved is None or not resolved.is_file():
        raise ValueError(f"artifact 不存在或越界: {path!r}")
    relative = resolved.resolve().relative_to(root.resolve()).as_posix()
    return {
        "artifact_id": str(artifact_id),
        "kind": str(kind),
        "path": relative,
        "sha256": sha256_file(resolved),
    }


def pass_record(
    tc_id: str,
    *,
    runner: Mapping[str, Any],
    execution: Mapping[str, Any],
    assertions: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
    baseline_version: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    """构造 PASS 记录；给出 root 时立即按合同自检，不完整则抛 ValueError。"""
    record: dict[str, Any] = {
        "tc_id": str(tc_id),
        "baseline_version": str(baseline_version),
        "status": PASS,
        "runner": dict(runner),
        "execution": dict(execution),
        "assertions": [dict(item) for item in assertions],
        "artifacts": [dict(item) for item in artifacts],
        "blocked_reason": None,
    }
    if root is not None:
        errors = record_errors(
            record,
            expected_commit=str(execution.get("tested_commit_sha") or ""),
            expected_environment=str(execution.get("environment") or ""),
            root=root,
        )
        if errors:
            raise ValueError("PASS 记录不满足 runner 合同: " + "; ".join(errors))
    return record


def non_pass_record(
    tc_id: str,
    *,
    reason: str,
    status: str = BLOCKED,
    runner: object = None,
    blocked: Mapping[str, Any] | None = None,
    baseline_version: str = "",
    started_at: str = "",
    finished_at: str = "",
) -> dict[str, Any]:
    """构造 BLOCKED/FAIL/NOT_PROVEN 等非 PASS 记录；必须带原因，不伪造执行 ID。"""
    normalized = str(status or "").strip().upper()
    if normalized == PASS:
        raise ValueError("non_pass_record 不允许构造 PASS")
    if normalized not in _NON_PASS_STATUSES:
        raise ValueError(f"非 PASS 状态非法: {status!r}")
    if not str(reason or "").strip():
        raise ValueError(f"{normalized} 必须给出原因")
    record: dict[str, Any] = {
        "tc_id": str(tc_id),
        "baseline_version": str(baseline_version),
        "status": normalized,
        "runner": runner_metadata(runner),
        "execution": None,
        "assertions": [],
        "artifacts": [],
        "blocked_reason": str(reason),
        "blocked": dict(blocked or {}),
    }
    if started_at:
        record["started_at"] = str(started_at)
    if finished_at:
        record["finished_at"] = str(finished_at)
        if started_at:
            record["duration_ms"] = int(duration_ms(started_at, finished_at) or 0)
    return record


def write_result(path: str | Path, record: Mapping[str, Any]) -> Path:
    """把单条 TC 结果写到 runner 结果路径；结构非法直接拒绝。"""
    target = Path(path)
    if not isinstance(record, Mapping):
        raise ValueError("TC 结果必须是 JSON 对象")
    tc_id = str(record.get("tc_id") or "").strip()
    if tc_id not in TC_IDS:
        raise ValueError(f"tc_id 非法: {tc_id!r}")
    status = str(record.get("status") or "").strip().upper()
    if status not in STATUSES:
        raise ValueError(f"非法状态: {status!r}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def _artifact_errors(
    artifacts: object, required_kinds: Sequence[str], *, root: Path
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    verified: list[str] = []
    if not isinstance(artifacts, list) or not artifacts:
        return ["缺少 artifacts（PASS 必须有可核验产物）"], verified
    kinds: set[str] = set()
    for index, artifact in enumerate(artifacts, 1):
        if not isinstance(artifact, Mapping):
            errors.append(f"artifacts[{index}] 不是对象")
            continue
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        kind = str(artifact.get("kind") or "").strip()
        if not artifact_id:
            errors.append(f"artifacts[{index}] 缺少 artifact_id")
        if kind:
            kinds.add(kind)
        else:
            errors.append(f"artifacts[{index}] 缺少 kind")
        raw_path = artifact.get("path") or artifact.get("ref")
        resolved = resolve_repo_path(root, raw_path)
        if resolved is None or not resolved.is_file():
            errors.append(f"artifact 不可读取或越界: {raw_path!r}")
            continue
        expected = str(artifact.get("sha256") or "").strip().lower()
        if not is_sha256(expected):
            errors.append(f"artifact {raw_path!r} 缺少合法 sha256")
            continue
        actual = sha256_file(resolved)
        if actual != expected.removeprefix("sha256:"):
            errors.append(f"artifact {raw_path!r} hash 不匹配（实际 {actual[:12]}）")
            continue
        verified.append(f"{raw_path}#sha256:{actual[:12]}")
    for required in required_kinds:
        if required not in kinds:
            errors.append(f"缺少必需 artifact kind: {required}")
    return errors, verified


def _assertion_errors(
    assertions: object, required_assertions: Sequence[str]
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    passed: list[str] = []
    if not isinstance(assertions, list) or not assertions:
        return ["缺少业务断言结果（PASS 至少需要一条强制业务断言）"], passed
    seen: set[str] = set()
    for index, item in enumerate(assertions, 1):
        if not isinstance(item, Mapping):
            errors.append(f"assertions[{index}] 不是对象")
            continue
        assertion_id = str(item.get("assertion_id") or "").strip()
        status = str(item.get("status") or "").strip().upper()
        if not assertion_id:
            errors.append(f"assertions[{index}] 缺少 assertion_id")
            continue
        if assertion_id in seen:
            errors.append(f"断言 {assertion_id} 重复")
        seen.add(assertion_id)
        if status != PASS:
            errors.append(f"断言 {assertion_id} 状态为 {status or '<empty>'}，不能 PASS")
            continue
        if not str(item.get("evidence_ref") or "").strip():
            errors.append(f"断言 {assertion_id} 缺少 evidence_ref")
            continue
        passed.append(assertion_id)
    for required in required_assertions:
        if required not in passed:
            errors.append(f"缺少强制业务断言或未通过: {required}")
    return errors, passed


def record_errors(
    record: object,
    *,
    case: Mapping[str, Any] | None = None,
    expected_commit: str = "",
    expected_environment: str = "",
    root: Path | None = None,
) -> list[str]:
    """校验单条 TC 结果是否满足 runner 合同（PASS 门槛 + 非 PASS 原因）。"""
    errors: list[str] = []
    if not isinstance(record, Mapping):
        return ["TC 结果不是对象"]
    tc_id = str(record.get("tc_id") or "").strip()
    if tc_id not in TC_IDS:
        errors.append(f"tc_id 非法: {tc_id!r}")
    status = str(record.get("status") or "").strip().upper()
    if status not in STATUSES:
        return errors + [f"{tc_id}: 非法状态 {status!r}"]
    if status != PASS:
        reason = next(
            (str(record.get(field) or "").strip() for field in _REASON_FIELDS if str(record.get(field) or "").strip()),
            "",
        )
        if not reason:
            errors.append(f"{tc_id}: {status} 必须给出 blocked_reason/原因")
        return errors

    if str(record.get("blocked_reason") or "").strip():
        errors.append(f"{tc_id}: PASS 记录不应包含 blocked_reason")
    runner = record.get("runner")
    if not runner_is_declared(runner):
        errors.append(f"{tc_id}: PASS 缺少已注册 runner（name/type/version/entrypoint）")
    else:
        runner_type = str(runner.get("type") or "").strip()
        if runner_type not in RUNNER_TYPES:
            errors.append(f"{tc_id}: PASS runner.type={runner_type!r} 未注册")
        case_runner = (case or {}).get("runner") if isinstance(case, Mapping) else None
        if isinstance(case_runner, Mapping):
            for key in ("type", "version", "entrypoint"):
                expected_value = str(case_runner.get(key) or "").strip()
                actual_value = str(runner.get(key) or "").strip()
                if expected_value and actual_value != expected_value:
                    errors.append(
                        f"{tc_id}: 结果 runner.{key}={actual_value!r} 与配置 {expected_value!r} 不一致"
                    )

    execution = record.get("execution")
    if not isinstance(execution, Mapping) or not execution:
        errors.append(f"{tc_id}: PASS 缺少 execution 块（run/job/SHA/环境/起止时间）")
        execution = {}
    run_id = str(execution.get("run_id") or execution.get("execution_id") or "").strip()
    if not run_id:
        errors.append(f"{tc_id}: PASS 缺少 run_id/execution_id")
    if not str(execution.get("job_id") or "").strip():
        errors.append(f"{tc_id}: PASS 缺少 job_id")
    tested_sha = str(execution.get("tested_commit_sha") or record.get("tested_commit_sha") or "").strip().lower()
    if not is_sha(tested_sha):
        errors.append(f"{tc_id}: PASS 缺少合法 tested_commit_sha")
    elif str(expected_commit or "").strip() and tested_sha != str(expected_commit).strip().lower():
        errors.append(f"{tc_id}: tested_commit_sha={tested_sha[:12]} 与本次验收 SHA 不一致")
    run_environment = str(execution.get("environment") or record.get("environment") or "").strip()
    if not run_environment:
        errors.append(f"{tc_id}: PASS 缺少 environment")
    elif expected_environment and run_environment != expected_environment:
        errors.append(f"{tc_id}: environment={run_environment} 与要求 {expected_environment} 不一致")
    started, finished = execution.get("started_at"), execution.get("finished_at")
    measured = duration_ms(started, finished)
    if measured is None:
        errors.append(f"{tc_id}: PASS 缺少有效 started_at/finished_at（或 finished 早于 started）")
    try:
        reported_duration = int(execution.get("duration_ms"))
    except (TypeError, ValueError):
        reported_duration = -1
    if reported_duration <= 0:
        errors.append(f"{tc_id}: duration_ms={execution.get('duration_ms')!r}，不能作为真实执行记录")
    elif measured is not None:
        tolerance = max(TIME_TOLERANCE_MIN_MS, int(reported_duration * TIME_TOLERANCE_RATIO))
        if abs(measured - reported_duration) > tolerance:
            errors.append(
                f"{tc_id}: duration_ms={reported_duration} 与时间跨度 {measured}ms 不一致"
            )

    required_assertions = [str(item) for item in (case or {}).get("required_assertions") or []]
    assertion_errors, _ = _assertion_errors(record.get("assertions"), required_assertions)
    errors.extend(f"{tc_id}: {item}" for item in assertion_errors)

    if root is None:
        errors.append(f"{tc_id}: 缺少 artifact 校验 root，无法核验产物真实性")
    else:
        required_artifacts = [str(item) for item in (case or {}).get("required_artifacts") or []]
        artifact_errors, _ = _artifact_errors(
            record.get("artifacts"), required_artifacts, root=root
        )
        errors.extend(f"{tc_id}: {item}" for item in artifact_errors)
    return errors


def summarize(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {status: 0 for status in STATUSES}
    for record in records:
        status = str((record or {}).get("status") or "").strip().upper()
        counts[status if status in STATUSES else UNKNOWN] += 1
    total = len(records)
    return {
        **counts,
        "total": total,
        "product_tc_pass": counts[PASS],
        "product_tc_total": total,
        "executed": counts[PASS] + counts[FAIL],
        "ga_ready": bool(total) and counts[PASS] == total,
    }


__all__ = [
    "ALLOWED_ENVIRONMENTS",
    "ARTIFACT_KIND",
    "CONFIG_SCHEMA_VERSION",
    "MANDATORY_BLOCKED_FIELDS",
    "MANDATORY_CASE_FIELDS_V2",
    "RUNNER_TYPES",
    "SCHEMA_VERSION",
    "TC_IDS",
    "VERIFIER_NAME",
    "VERIFIER_VERSION",
    "artifact_entry",
    "assertion_result",
    "config_schema_is_v2",
    "environment_errors",
    "execution_block",
    "iso_now",
    "is_sha",
    "non_pass_record",
    "now_utc",
    "pass_record",
    "record_errors",
    "runner_argv",
    "runner_entrypoint",
    "runner_is_declared",
    "runner_metadata",
    "summarize",
    "validate_config",
    "write_result",
]
