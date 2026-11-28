"""V16-017 / V1.6.2 FIX-002：产品级 TC（TC-AIQE-001..010）统一执行编排。

模式（互斥）
------------
``--check-config``    只校验配置结构，输出 ``CONFIG_VALID``；不得出现产品 PASS 字样。
``--plan``            解析并列出本次将执行的 TC 与阻塞原因，**不执行**。
``--run``             通过正式 runner 入口执行；每条 TC 写出结构化记录
                      （runner / execution / assertions / artifacts / blocked_reason）。
``--verify-results``  调用 ``verify_product_tc_results.py`` 语义校验既有结果。

退出码
------
0   全部 10 条 TC PASS（或 ``--allow-blocked`` 且无 FAIL）
1   配置/合同/验证错误，或存在 FAIL
2   无 runner、缺环境变量等导致 BLOCKED/NOT_PROVEN（fail-closed，不伪造 PASS）

结果文件
--------
``--run`` 每次重新生成 ``product-results.json``：写入本次 ``baseline_version``、
``commit_sha``（优先 ``AIQE_TESTED_COMMIT_SHA``，否则 ``git rev-parse HEAD``）、
``verification`` 块与逐条执行记录。禁止手工维护该文件作为事实源；只有
``verify_product_tc_results.py`` 通过后，结果才可作为 Release Gate 输入。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from statuses import BLOCKED, NOT_PROVEN, PASS, STATUSES, normalize  # noqa: E402
from per_tc.runner_contract import (  # noqa: E402
    ARTIFACT_KIND,
    SCHEMA_VERSION,
    TC_IDS,
    VERIFIER_NAME,
    VERIFIER_VERSION,
    iso_now,
    is_sha,
    non_pass_record,
    record_errors,
    runner_argv,
    runner_metadata,
    summarize,
)

DEFAULT_CONFIG = ROOT / "docs/aiqe/v1.6/e2e/product-tc-config.yaml"
DEFAULT_OUTPUT = ROOT / "docs/aiqe/v1.6/e2e/product-results.json"
VERIFY_SCRIPT = SCRIPT_DIR / "verify_product_tc_results.py"
PLANNED_BLOCKED = "BLOCKED"
PLANNED_RUNNABLE = "RUNNABLE"


def load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def validate_config(config: Any, *, root: Path = ROOT) -> list[str]:
    """校验产品 TC 配置；具体合同规则见 ``per_tc/runner_contract.py``。"""
    from per_tc.runner_contract import validate_config as _validate

    return _validate(config, root=root)


def _baseline(config: Mapping[str, Any]) -> str:
    return str(config.get("baseline_version") or "").strip()


def _relative_ref(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _resolve_commit() -> str:
    """本次实际测试 SHA：优先 AIQE_TESTED_COMMIT_SHA，否则 git HEAD；非法即失败。"""
    explicit = os.environ.get("AIQE_TESTED_COMMIT_SHA", "").strip().lower()
    if explicit:
        if not is_sha(explicit):
            raise ValueError("AIQE_TESTED_COMMIT_SHA 必须是完整 40 位十六进制 SHA")
        return explicit
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"无法解析本次 checkout SHA: {exc}") from exc
    commit = completed.stdout.strip().lower()
    if not is_sha(commit):
        raise ValueError("git rev-parse HEAD 未返回合法 40 位 SHA")
    return commit


def _missing_env(config: Mapping[str, Any]) -> list[str]:
    required = [str(name) for name in config.get("required_env") or []]
    return [name for name in required if not os.environ.get(name)]


def _blocked_metadata(case: Mapping[str, Any]) -> dict[str, str]:
    return {
        "by": str(case.get("blocked_by") or ""),
        "owner": str(case.get("owner") or ""),
        "unblock_action": str(case.get("unblock_action") or ""),
        "blocked_status": str(case.get("blocked_status") or BLOCKED).upper(),
    }


def plan_entry(case: Mapping[str, Any]) -> dict[str, Any]:
    runner = case.get("runner")
    executable = runner_argv(runner) is not None
    return {
        "tc_id": str(case.get("tc_id") or ""),
        "title": str(case.get("title") or ""),
        "baseline_version": str(case.get("baseline_version") or ""),
        "required_environment": str(case.get("required_environment") or ""),
        "runner": runner_metadata(runner),
        "required_assertions": [str(item) for item in case.get("required_assertions") or []],
        "required_artifacts": [str(item) for item in case.get("required_artifacts") or []],
        "timeout_seconds": case.get("timeout_seconds"),
        "planned_status": PLANNED_RUNNABLE if executable else PLANNED_BLOCKED,
        "blocked_reason": "" if executable else str(case.get("blocked_by") or "未配置 runner"),
        "owner": str(case.get("owner") or ""),
        "unblock_action": str(case.get("unblock_action") or ""),
    }


def build_plan(config: Mapping[str, Any]) -> dict[str, Any]:
    cases = [case for case in config.get("test_cases") or [] if isinstance(case, Mapping)]
    return {
        "artifact_kind": "product-tc-plan",
        "schema_version": SCHEMA_VERSION,
        "baseline_version": _baseline(config),
        "environment": str(config.get("environment") or ""),
        "cases": [plan_entry(case) for case in cases],
        "summary": {
            "total": len(cases),
            PLANNED_RUNNABLE: sum(1 for case in cases if runner_argv(case.get("runner")) is not None),
            PLANNED_BLOCKED: sum(1 for case in cases if runner_argv(case.get("runner")) is None),
        },
    }


def _normalize_runner_result(
    raw: Mapping[str, Any],
    *,
    case: Mapping[str, Any],
    commit_sha: str,
    environment: str,
    root: Path,
) -> dict[str, Any]:
    """把 runner 写回的结果收敛到统一合同；PASS 不完整就降级为 NOT_PROVEN。"""
    tc_id = str(case["tc_id"])
    record = dict(raw)
    raw_tc_id = str(raw.get("tc_id") or "").strip()
    if raw_tc_id and raw_tc_id != tc_id:
        return non_pass_record(
            tc_id,
            status=NOT_PROVEN,
            reason=f"runner 返回 tc_id={raw_tc_id} 与配置 {tc_id} 不一致",
            runner=case.get("runner"),
            baseline_version=str(case.get("baseline_version") or ""),
        )
    record["tc_id"] = tc_id
    record["baseline_version"] = str(case.get("baseline_version") or "")
    status = str(raw.get("status") or "").strip().upper()
    if status in STATUSES:
        normalized = status
    elif not status:
        normalized = NOT_PROVEN
    else:
        normalized = normalize(status)
    record["status"] = normalized
    if normalized != status:
        record["raw_status"] = status
    if not isinstance(record.get("runner"), Mapping):
        record["runner"] = runner_metadata(case.get("runner"))
    elif str(record["runner"].get("entrypoint") or "").strip() == "":
        configured = runner_metadata(case.get("runner"))
        record["runner"] = {**dict(record["runner"]), "entrypoint": configured.get("entrypoint")}
    record.setdefault("assertions", [])
    record.setdefault("artifacts", [])
    record.setdefault("blocked_reason", None)
    if normalized == NOT_PROVEN and not str(record.get("blocked_reason") or "").strip():
        record["blocked_reason"] = f"runner 返回无法识别或不完整的状态 {status!r}，已按 NOT_PROVEN 处理"
    errors = record_errors(
        record,
        case=case,
        expected_commit=commit_sha,
        expected_environment=environment,
        root=root,
    )
    if errors:
        record["contract_errors"] = errors
        if record["status"] == PASS:
            record["claimed_status"] = PASS
            record["status"] = NOT_PROVEN
            record["blocked_reason"] = "runner 声称 PASS 但 runner 合同不完整: " + "; ".join(errors)
        elif not str(record.get("blocked_reason") or "").strip():
            record["blocked_reason"] = "; ".join(errors)
    return record


def _tail(text: str, limit: int = 400) -> str:
    return (text or "").strip()[-limit:]


def run_case(
    case: Mapping[str, Any],
    *,
    commit_sha: str,
    environment: str,
    root: Path,
    missing_env: list[str],
) -> dict[str, Any]:
    tc_id = str(case["tc_id"])
    baseline = str(case.get("baseline_version") or "")
    runner = case.get("runner")
    argv = runner_argv(runner)
    started_at = iso_now()
    if argv is None:
        return non_pass_record(
            tc_id,
            status=BLOCKED,
            reason=str(case.get("blocked_by") or "未配置 runner"),
            runner=runner,
            blocked=_blocked_metadata(case),
            baseline_version=baseline,
            started_at=started_at,
            finished_at=iso_now(),
        )
    if missing_env:
        return non_pass_record(
            tc_id,
            status=BLOCKED,
            reason="缺少必需环境变量: " + ", ".join(missing_env),
            runner=runner,
            blocked=_blocked_metadata(case),
            baseline_version=baseline,
            started_at=started_at,
            finished_at=iso_now(),
        )
    try:
        timeout_seconds = int(case.get("timeout_seconds") or 900)
    except (TypeError, ValueError):
        timeout_seconds = 900
    with tempfile.TemporaryDirectory(prefix=f"aiqe-{tc_id}-") as tmp:
        result_path = Path(tmp) / "result.json"
        env = dict(os.environ)
        env.update(
            {
                "AIQE_TC_RESULT_PATH": str(result_path),
                "AIQE_TC_ID": tc_id,
                "AIQE_TC_ROOT": str(root),
                "AIQE_TESTED_COMMIT_SHA": commit_sha,
                "AIQE_TC_ENVIRONMENT": environment,
                "AIQE_AIQE_SCRIPTS_DIR": str(SCRIPT_DIR),
            }
        )
        try:
            completed = subprocess.run(
                argv,
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return non_pass_record(
                tc_id,
                status=BLOCKED,
                reason=f"runner 超时（>{timeout_seconds}s），不能记为 PASS",
                runner=runner,
                blocked=_blocked_metadata(case),
                baseline_version=baseline,
                started_at=started_at,
                finished_at=iso_now(),
            )
        finished_at = iso_now()
        if not result_path.is_file():
            output = _tail(completed.stderr) or _tail(completed.stdout) or "<no output>"
            return non_pass_record(
                tc_id,
                status=NOT_PROVEN,
                reason=f"runner 未写出机器结果（exit={completed.returncode}）: {output}",
                runner=runner,
                baseline_version=baseline,
                started_at=started_at,
                finished_at=finished_at,
            )
        try:
            raw = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return non_pass_record(
                tc_id,
                status=NOT_PROVEN,
                reason=f"runner 机器结果不是合法 JSON: {exc}",
                runner=runner,
                baseline_version=baseline,
                started_at=started_at,
                finished_at=finished_at,
            )
        if not isinstance(raw, Mapping):
            return non_pass_record(
                tc_id,
                status=NOT_PROVEN,
                reason="runner 机器结果不是 JSON 对象",
                runner=runner,
                baseline_version=baseline,
                started_at=started_at,
                finished_at=finished_at,
            )
        record = _normalize_runner_result(
            raw, case=case, commit_sha=commit_sha, environment=environment, root=root
        )
        record["runner_exit_code"] = completed.returncode
        if completed.returncode != 0 and record.get("status") == PASS:
            record["claimed_status"] = PASS
            record["status"] = NOT_PROVEN
            record["blocked_reason"] = (
                f"runner 退出码 {completed.returncode} 却声称 PASS，不能作为通过证据"
            )
        return record


def build_results(
    config: Mapping[str, Any],
    *,
    commit_sha: str,
    environment: str,
    root: Path,
    config_ref: str = "",
) -> dict[str, Any]:
    missing_env = _missing_env(config)
    cases = [case for case in config.get("test_cases") or [] if isinstance(case, Mapping)]
    records = [
        run_case(
            case,
            commit_sha=commit_sha,
            environment=environment,
            root=root,
            missing_env=missing_env,
        )
        for case in cases
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "baseline_version": _baseline(config),
        "adr_ref": str(config.get("adr_ref") or ""),
        "config_ref": config_ref,
        "commit_sha": commit_sha,
        "environment": environment,
        "generated_at": iso_now(),
        "verification": {
            "verified": False,
            "verified_commit_sha": None,
            "verified_at": None,
            "verifier": {"name": VERIFIER_NAME, "version": VERIFIER_VERSION},
            "errors": ["尚未执行 scripts/aiqe/verify_product_tc_results.py"],
            "results_sha256": None,
        },
        "tests": records,
        "summary": summarize(records),
    }


def write_results(path: Path, results: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(results), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_product_tc_results", VERIFY_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载验证器: {VERIFY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_verify(args: argparse.Namespace, root: Path) -> int:
    module = _load_verifier()
    verify_argv = [
        "--config",
        str(Path(args.config)),
        "--results",
        str(Path(args.output)),
        "--root",
        str(root),
    ]
    expected = os.environ.get("AIQE_TESTED_COMMIT_SHA", "").strip()
    if expected:
        verify_argv.extend(["--expected-commit", expected])
    if args.require_pass:
        verify_argv.append("--require-pass")
    return int(module.main(verify_argv))


def _reconfigure_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass


def main(argv: list[str] | None = None) -> int:
    _reconfigure_streams()
    parser = argparse.ArgumentParser(description="产品级 TC 统一执行编排（V1.6.2 FIX-002）")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--root", default=str(ROOT), help="仓库/fixture 根目录（artifact 路径解析）")
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--verify-results", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="存在 BLOCKED/NOT_PROVEN 时仍返回 0（仍不允许 FAIL）",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="配合 --verify-results：任一 TC 非 PASS 或校验错误时非零退出",
    )
    args = parser.parse_args(argv)
    modes = [args.check_config, args.plan, args.run, args.verify_results]
    if sum(1 for mode in modes if mode) != 1:
        print(
            "::error::[product-tc] 必须且只能指定 --check-config / --plan / --run / --verify-results 之一",
            file=sys.stderr,
        )
        return 1
    root = Path(args.root).resolve()
    config_path = Path(args.config)
    try:
        config = load_config(config_path)
    except (OSError, yaml.YAMLError) as exc:
        print(f"::error::[product-tc] 无法读取配置 {config_path}: {exc}", file=sys.stderr)
        return 1
    errors = validate_config(config, root=root)
    for error in errors:
        print(f"::error::[product-tc] {error}", file=sys.stderr)
    if args.check_config:
        if errors:
            print("CONFIG_INVALID")
            return 1
        print(
            "CONFIG_VALID "
            + json.dumps(
                {
                    "cases": len(config.get("test_cases") or []),
                    "schema_version": str(config.get("schema_version") or ""),
                    "baseline_version": _baseline(config),
                    "environment": str(config.get("environment") or ""),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.plan:
        if errors:
            return 1
        print(json.dumps(build_plan(config), ensure_ascii=False, indent=2))
        return 0
    if args.verify_results:
        return _run_verify(args, root)
    if errors:
        return 1
    try:
        commit_sha = _resolve_commit()
    except ValueError as exc:
        print(f"::error::[product-tc] {exc}", file=sys.stderr)
        return 1
    environment = str(config.get("environment") or "").strip()
    results = build_results(
        config,
        commit_sha=commit_sha,
        environment=environment,
        root=root,
        config_ref=_relative_ref(root, config_path),
    )
    output = Path(args.output)
    write_results(output, results)
    summary = results["summary"]
    print(json.dumps(summary, ensure_ascii=False))
    if summary["FAIL"]:
        return 1
    if summary["product_tc_pass"] == len(TC_IDS):
        return 0
    if args.allow_blocked:
        return 0
    print(
        "::error::[product-tc] 产品 TC 未全部通过，BLOCKED/NOT_PROVEN 不计为 PASS；"
        "结果已按 BLOCKED/NOT_PROVEN 写入，退出码 2",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
