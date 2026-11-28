"""产品 TC 配置 / 执行结果语义校验（FIX-001 / FIX-002 / FIX-003）。

关键立场
--------
- 配置里的 ``runner: null`` 只有在同时给出 ``blocked_by/owner/unblock_action``
  时才算“显式 BLOCKED”；无解释的 null 直接不通过。
- 静态 JSON 里的 10/10 不是证据：PASS 必须来自本次 ``product-results.json``，
  带 approval baseline、execution id、测试 SHA、环境、逐条业务断言与可核验 artifact。
- 任何一条 TC 非 PASS，产品级 Gate 就非 PASS，不允许“9 条通过算整体通过”。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from statuses import FAIL, NOT_PROVEN, PASS
from validators.common import (
    duration_ms,
    is_sha,
    is_sha256,
    resolve_repo_path,
    sha256_file,
)
from validators.models import GateCheck

TC_IDS = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))
RUNNER_TYPES = {"api_worker_e2e", "api_e2e", "ui_e2e", "external_runner", "db_readonly", "benchmark_e2e"}


def _runner_entrypoint(runner: Any) -> str:
    if isinstance(runner, dict):
        return str(runner.get("entrypoint") or "").strip()
    if isinstance(runner, list) and runner:
        items = [str(item) for item in runner]
        if Path(items[0]).name.lower() in {"python", "python3", "python.exe"} and len(items) > 1:
            return items[1]
        return items[0]
    return ""


def runner_is_declared(runner: Any) -> bool:
    if isinstance(runner, dict):
        return bool(
            str(runner.get("type") or "").strip()
            and str(runner.get("version") or "").strip()
            and str(runner.get("entrypoint") or "").strip()
        )
    if isinstance(runner, list):
        return bool(runner)
    return False


def validate_product_config(
    config: Any,
    *,
    expected_baseline: str = "",
    root: Path | None = None,
) -> GateCheck:
    check = GateCheck()
    check.status = PASS
    if not isinstance(config, dict) or not config:
        return GateCheck.unproven("缺少 product-tc-config.yaml 或格式非法")
    cases = config.get("test_cases") or []
    if not isinstance(cases, list):
        return GateCheck.unproven("product-tc-config.test_cases 必须是列表")
    ids = [str(case.get("tc_id") or "").strip() for case in cases if isinstance(case, dict)]
    if len(ids) != len(set(ids)):
        check.add("product-tc-config 存在重复 tc_id")
    missing = [tc_id for tc_id in TC_IDS if tc_id not in ids]
    extra = [tc_id for tc_id in ids if tc_id not in TC_IDS]
    if missing:
        check.add(f"product-tc-config 缺少 TC: {missing}")
    if extra:
        check.add(f"product-tc-config 含未批准 TC: {extra}")
    baseline = str(config.get("baseline_version") or "").strip()
    if not baseline:
        check.add("product-tc-config 缺少 baseline_version")
    elif expected_baseline and baseline != expected_baseline:
        check.add(f"product-tc-config baseline_version={baseline} 与批准基线 {expected_baseline} 不一致")
    if not str(config.get("environment") or "").strip():
        check.add("product-tc-config 缺少 environment")
    for case in cases:
        if not isinstance(case, dict):
            check.add("product-tc-config.test_cases 含非对象条目")
            continue
        tc_id = str(case.get("tc_id") or "?")
        if not str(case.get("title") or "").strip():
            check.add(f"{tc_id}: 缺少 title")
        if not str(case.get("spec_ref") or "").strip():
            check.add(f"{tc_id}: 缺少 spec_ref")
        case_baseline = str(case.get("baseline_version") or "").strip()
        if case_baseline and baseline and case_baseline != baseline:
            check.add(f"{tc_id}: baseline_version={case_baseline} 与全局 {baseline} 不一致")
        runner = case.get("runner")
        if runner_is_declared(runner):
            entrypoint = _runner_entrypoint(runner)
            if not entrypoint:
                check.add(f"{tc_id}: runner 缺少 entrypoint")
            elif root is not None:
                script = resolve_repo_path(root, entrypoint)
                if script is None or not script.exists():
                    check.add(f"{tc_id}: runner 入口不存在或越界: {entrypoint}")
            if isinstance(runner, dict):
                runner_type = str(runner.get("type") or "").strip()
                if runner_type and runner_type not in RUNNER_TYPES:
                    check.add(f"{tc_id}: 未注册的 runner.type {runner_type!r}")
                if not str(runner.get("version") or "").strip():
                    check.add(f"{tc_id}: runner 缺少 version")
        elif runner is None:
            for field in ("blocked_by", "owner", "unblock_action"):
                if not str(case.get(field) or "").strip():
                    check.add(f"{tc_id}: runner 为空时必须显式填写 {field}")
            blocked_status = str(case.get("blocked_status") or "BLOCKED").upper()
            if blocked_status == PASS:
                check.add(f"{tc_id}: runner 为空时 blocked_status 不能是 PASS")
        else:
            check.add(f"{tc_id}: runner 结构非法: {runner!r}")
        for key in ("required_assertions", "required_artifacts", "required_secrets", "preconditions"):
            value = case.get(key, [])
            if value is not None and not isinstance(value, list):
                check.add(f"{tc_id}: {key} 必须是列表")
    if check.status == PASS:
        check.note(
            f"产品 TC 配置通过：{len(cases)} 条，baseline={baseline or '<未声明>'}，"
            "所有空 runner 均有显式 BLOCKED 说明"
        )
    return check


def _artifact_check(
    artifacts: Any,
    required_kinds: list[str],
    *,
    root: Path,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    verified: list[str] = []
    if not isinstance(artifacts, list) or not artifacts:
        return ["缺少 artifacts（PASS 必须有可核验产物）"], verified
    kinds: set[str] = set()
    for index, artifact in enumerate(artifacts, 1):
        if not isinstance(artifact, dict):
            errors.append(f"artifacts[{index}] 不是对象")
            continue
        kind = str(artifact.get("kind") or artifact.get("artifact_id") or "").strip()
        if kind:
            kinds.add(kind)
        raw_path = artifact.get("path") or artifact.get("ref")
        path = resolve_repo_path(root, raw_path)
        if path is None or not path.exists() or not path.is_file():
            errors.append(f"artifact 不可读取或越界: {raw_path!r}")
            continue
        expected_hash = str(artifact.get("sha256") or "").strip().lower()
        if not is_sha256(expected_hash):
            errors.append(f"artifact {raw_path!r} 缺少 sha256")
            continue
        actual = sha256_file(path)
        if actual != expected_hash.removeprefix("sha256:"):
            errors.append(f"artifact {raw_path!r} hash 不匹配（实际 {actual[:12]}）")
            continue
        verified.append(f"{raw_path}#sha256:{actual[:12]}")
    for required in required_kinds:
        if required not in kinds:
            errors.append(f"缺少必需 artifact kind: {required}")
    return errors, verified


def _assertions_check(
    assertions: Any, required: list[str]
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    passed_ids: list[str] = []
    if not isinstance(assertions, list) or not assertions:
        return ["缺少业务断言结果（PASS 至少需要一条强制业务断言）"], passed_ids
    for index, item in enumerate(assertions, 1):
        if not isinstance(item, dict):
            errors.append(f"assertions[{index}] 不是对象")
            continue
        assertion_id = str(item.get("assertion_id") or item.get("id") or "").strip()
        status = str(item.get("status") or "").strip().upper()
        if not assertion_id:
            errors.append(f"assertions[{index}] 缺少 assertion_id")
        if status != PASS:
            errors.append(f"断言 {assertion_id or index} 状态为 {status or '<empty>'}，不能 PASS")
        else:
            passed_ids.append(assertion_id)
    for required_id in required:
        if required_id not in passed_ids:
            errors.append(f"缺少强制业务断言或未通过: {required_id}")
    return errors, passed_ids


def validate_product_results(
    results: Any,
    config: Any,
    *,
    expected_commit: str,
    expected_environment: str = "",
    root: Path | None = None,
    require_verified: bool = True,
    require_baseline: bool = True,
) -> GateCheck:
    check = GateCheck()
    check.status = PASS
    if root is None:
        raise ValueError("validate_product_results 需要 root 解析 artifact 路径")
    if not isinstance(results, dict) or not results:
        return GateCheck.unproven("缺少 product-results.json 或格式非法")
    if str(results.get("status") or "").upper() == NOT_PROVEN:
        return GateCheck.unproven(
            "product-results.json 标记 NOT_PROVEN: " + str(results.get("reason") or "")
        )

    config_baseline = str((config or {}).get("baseline_version") or "").strip()
    result_baseline = str(results.get("baseline_version") or "").strip()
    if require_baseline:
        if not result_baseline:
            check.add("product-results 缺少 baseline_version，无法证明与批准基线一致")
        elif config_baseline and result_baseline != config_baseline:
            check.add(
                f"product-results baseline_version={result_baseline} 与配置 {config_baseline} 不一致"
            )

    commit = str(results.get("commit_sha") or results.get("tested_commit_sha") or "").strip().lower()
    if not is_sha(commit):
        check.add("product-results 缺少合法 commit_sha/tested_commit_sha")
    elif str(expected_commit).strip().lower() and commit != str(expected_commit).strip().lower():
        check.add(
            f"product-results commit_sha={commit[:12]} 与实际测试 SHA {str(expected_commit)[:12]} 不一致"
        )
    environment = str(results.get("environment") or "").strip()
    if not environment:
        check.add("product-results 缺少 environment")
    elif expected_environment and environment != expected_environment:
        check.add(f"product-results environment={environment} 与要求 {expected_environment} 不一致")

    if require_verified:
        verification = results.get("verification") or {}
        if not isinstance(verification, dict) or verification.get("verified") is not True:
            check.add("product-results 未经 --verify-results 语义验证（verification.verified!=true）")
        else:
            verified_sha = str(verification.get("verified_commit_sha") or "").strip().lower()
            if not is_sha(verified_sha):
                check.add("product-results verification 缺少 verified_commit_sha")
            elif commit and verified_sha != commit:
                check.add("product-results verification.verified_commit_sha 与 commit_sha 不一致")
            if verification.get("errors"):
                check.add(f"product-results verification 仍有错误: {verification.get('errors')}")

    cases = {
        str(case.get("tc_id")): case
        for case in (config or {}).get("test_cases") or []
        if isinstance(case, dict)
    }
    tests = results.get("tests") or []
    if not isinstance(tests, list) or not tests:
        return GateCheck.unproven("product-results 没有 tests 记录")
    ids = [str(item.get("tc_id") or "").strip() for item in tests if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        check.add("product-results 存在重复 TC")
    if sorted(ids) != sorted(TC_IDS):
        check.add(f"product-results TC 集合不等于批准的 10 条基线（实际 {sorted(ids)}）")

    summary_pass = 0
    for item in tests:
        if not isinstance(item, dict):
            check.add("product-results 含非对象 TC 记录")
            continue
        tc_id = str(item.get("tc_id") or "?").strip()
        status = str(item.get("status") or "").strip().upper()
        if status != PASS:
            if status == FAIL:
                check.demote(FAIL)
                check.add(f"{tc_id}: FAIL")
            else:
                check.add(f"{tc_id}: 状态 {status or '<empty>'} 不能计入产品 PASS")
            continue
        summary_pass += 1
        case = cases.get(tc_id, {})

        runner = item.get("runner")
        if not isinstance(runner, dict) or not runner_is_declared(runner):
            check.add(f"{tc_id}: PASS 缺少已注册 runner（name/type/version）")
        else:
            config_runner = case.get("runner") if isinstance(case, dict) else None
            if runner_is_declared(config_runner):
                for key in ("type", "version"):
                    if str(runner.get(key) or "") != str(config_runner.get(key) or ""):
                        check.add(f"{tc_id}: 结果 runner.{key} 与配置不一致")

        execution = item.get("execution") if isinstance(item.get("execution"), dict) else {}
        if not execution:
            check.add(f"{tc_id}: PASS 缺少 execution 块（run/job/SHA/环境/起止时间）")
            execution = item
        run_id = str(execution.get("run_id") or execution.get("execution_id") or "").strip()
        job_id = str(execution.get("job_id") or "").strip()
        if not run_id:
            check.add(f"{tc_id}: PASS 缺少 run_id/execution_id")
        if not job_id:
            check.add(f"{tc_id}: PASS 缺少 job_id")
        tested_sha = str(execution.get("tested_commit_sha") or item.get("tested_commit_sha") or "").strip().lower()
        if not is_sha(tested_sha):
            check.add(f"{tc_id}: PASS 缺少 tested_commit_sha")
        elif tested_sha != str(expected_commit).strip().lower():
            check.add(f"{tc_id}: tested_commit_sha={tested_sha[:12]} 与本次验收 SHA 不一致")
        run_environment = str(execution.get("environment") or item.get("environment") or "").strip()
        if not run_environment:
            check.add(f"{tc_id}: PASS 缺少 environment")
        elif expected_environment and run_environment != expected_environment:
            check.add(f"{tc_id}: environment={run_environment} 与要求 {expected_environment} 不一致")
        started, finished = execution.get("started_at"), execution.get("finished_at")
        measured = duration_ms(started, finished)
        if measured is None:
            check.add(f"{tc_id}: PASS 缺少有效 started_at/finished_at")
        try:
            reported_duration = int(execution.get("duration_ms"))
        except (TypeError, ValueError):
            reported_duration = -1
        if reported_duration <= 0:
            check.add(f"{tc_id}: duration_ms={execution.get('duration_ms')!r}，不能作为真实执行记录")
        elif measured is not None and abs(measured - reported_duration) > max(2000, reported_duration // 10):
            check.add(f"{tc_id}: duration_ms={reported_duration} 与时间跨度 {measured}ms 不一致")

        required_assertions = [str(x) for x in case.get("required_assertions") or []]
        assertion_errors, passed_assertions = _assertions_check(
            item.get("assertions"), required_assertions
        )
        for error in assertion_errors:
            check.add(f"{tc_id}: {error}")

        required_artifacts = [str(x) for x in case.get("required_artifacts") or []]
        artifact_errors, verified_artifacts = _artifact_check(
            item.get("artifacts"), required_artifacts, root=root
        )
        for error in artifact_errors:
            check.add(f"{tc_id}: {error}")
        if passed_assertions and verified_artifacts:
            check.note(
                f"{tc_id}: run={run_id} assertions={len(passed_assertions)} "
                f"artifacts={len(verified_artifacts)}"
            )

    summary = results.get("summary") or {}
    if int(summary.get("product_tc_pass") or 0) != summary_pass:
        check.add(
            f"product-results summary.product_tc_pass={summary.get('product_tc_pass')} "
            f"与逐条 PASS={summary_pass} 不一致"
        )
    if any(int(summary.get(key) or 0) for key in ("FAIL", "BLOCKED", "NOT_RUN")):
        check.add(
            "product-results 仍有非 PASS: "
            f"FAIL={summary.get('FAIL')} BLOCKED={summary.get('BLOCKED')} NOT_RUN={summary.get('NOT_RUN')}"
        )

    if check.status == PASS:
        check.note("产品 TC 结果逐条通过：runner/execution/SHA/环境/断言/artifact 均语义一致")
        check.evidence_refs.append("docs/aiqe/v1.6/e2e/product-results.json")
    return check


__all__ = [
    "TC_IDS",
    "runner_is_declared",
    "validate_product_config",
    "validate_product_results",
]
