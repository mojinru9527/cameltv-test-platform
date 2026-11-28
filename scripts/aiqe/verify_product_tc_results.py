"""V1.6.2 FIX-002：``product-results.json`` 语义验证与反伪造。

校验范围
--------
1. 配置：baseline_version / environment / 10 条 TC / 每条必需字段与显式 BLOCKED 元数据。
2. 文件级：schema、artifact_kind、baseline_version 与配置一致、environment 合法且与
   配置一致、commit_sha 合法且等于 ``--expected-commit``（缺省读
   ``AIQE_TESTED_COMMIT_SHA``，再退到 ``git rev-parse HEAD``）。
3. 逐条：PASS 必须满足 runner/execution/断言/artifact 合同；artifact 路径必须存在且
   sha256 匹配；duration_ms > 0 且与 started_at/finished_at 一致；非 PASS 必须有原因。
4. summary 计数与实际记录一致，``ga_ready`` 只能在全 PASS 时为真。
5. 伪造识别：配置没有 runner 时的手工 PASS、artifact hash 不匹配、复用旧 SHA、
   environment=local/production、验证后再次手工修改结果文件（digest 不匹配）都会拒绝。

写回
----
``results["verification"] = {verified, verified_commit_sha, verified_at,
verifier:{name,version}, errors, results_sha256}``；``--require-pass`` 时任一 TC
非 PASS 或存在错误即非零退出。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from statuses import PASS  # noqa: E402
from per_tc.runner_contract import (  # noqa: E402
    ARTIFACT_KIND,
    SCHEMA_VERSION,
    TC_IDS,
    VERIFIER_NAME,
    VERIFIER_VERSION,
    environment_errors,
    is_sha,
    iso_now,
    record_errors,
    runner_argv,
    summarize,
    validate_config,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "docs/aiqe/v1.6/e2e/product-tc-config.yaml"
DEFAULT_RESULTS = ROOT / "docs/aiqe/v1.6/e2e/product-results.json"
SUMMARY_KEYS = (
    "PASS",
    "FAIL",
    "BLOCKED",
    "NOT_RUN",
    "NOT_PROVEN",
    "PARTIAL",
    "WAIVED",
    "UNKNOWN",
    "total",
    "product_tc_pass",
    "ga_ready",
)


def canonical_digest(document: Mapping[str, Any]) -> str:
    """对除 verification 之外的规范化内容取 sha256，用于识别验证后的手工改写。"""
    payload = {key: value for key, value in document.items() if key != "verification"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_expected_commit(explicit: str = "") -> str:
    if str(explicit or "").strip():
        commit = str(explicit).strip().lower()
        if not is_sha(commit):
            raise ValueError("--expected-commit 必须是完整 40 位十六进制 SHA")
        return commit
    from_env = os.environ.get("AIQE_TESTED_COMMIT_SHA", "").strip().lower()
    if from_env:
        if not is_sha(from_env):
            raise ValueError("AIQE_TESTED_COMMIT_SHA 必须是完整 40 位十六进制 SHA")
        return from_env
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
        raise ValueError(f"无法解析本次 checkout SHA，请显式传入 --expected-commit: {exc}") from exc
    commit = completed.stdout.strip().lower()
    if not is_sha(commit):
        raise ValueError("git rev-parse HEAD 未返回合法 40 位 SHA")
    return commit


def _case_map(config: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(case.get("tc_id")): case
        for case in config.get("test_cases") or []
        if isinstance(case, Mapping)
    }


def _verify_summary(results: Mapping[str, Any], actual: Mapping[str, Any], errors: list[str]) -> None:
    summary = results.get("summary")
    if not isinstance(summary, Mapping):
        errors.append("product-results 缺少 summary")
        return
    for key in SUMMARY_KEYS:
        if key not in summary:
            errors.append(f"summary 缺少 {key}")
    for key in SUMMARY_KEYS[:-1]:
        if key not in summary:
            continue
        try:
            reported = int(summary.get(key))
        except (TypeError, ValueError):
            errors.append(f"summary.{key}={summary.get(key)!r} 不是整数")
            continue
        if reported != int(actual.get(key, 0)):
            errors.append(
                f"summary.{key}={reported} 与逐条统计 {int(actual.get(key, 0))} 不一致"
            )
    if "ga_ready" in summary and bool(summary.get("ga_ready")) != bool(actual["ga_ready"]):
        errors.append(
            f"summary.ga_ready={summary.get('ga_ready')!r} 与逐条统计 {actual['ga_ready']} 不一致"
        )
    if "product_tc_total" in summary:
        try:
            total = int(summary.get("product_tc_total"))
        except (TypeError, ValueError):
            errors.append(f"summary.product_tc_total={summary.get('product_tc_total')!r} 不是整数")
        else:
            if total != int(actual["total"]):
                errors.append(f"summary.product_tc_total={total} 与记录数 {actual['total']} 不一致")


def _verify_previous_verification(
    results: Mapping[str, Any], commit: str, errors: list[str]
) -> None:
    previous = results.get("verification")
    if not isinstance(previous, Mapping) or previous.get("verified") is not True:
        return
    if previous.get("errors"):
        errors.append("既有 verification.verified=true 但 errors 非空，验证块自相矛盾")
    previous_commit = str(previous.get("verified_commit_sha") or "").strip().lower()
    if not is_sha(previous_commit):
        errors.append("既有 verification.verified_commit_sha 非法，疑似伪造验证块")
    elif previous_commit != commit:
        errors.append(
            f"既有 verification 绑定 SHA {previous_commit[:12]} 与本次 {commit[:12]} 不一致"
            "（疑似复用旧结果）"
        )
    previous_digest = str(previous.get("results_sha256") or "").strip().lower()
    if not previous_digest:
        errors.append(
            "既有 verification 缺少 results_sha256，无法证明验证后未被手工修改；"
            "请用 --no-write 之外的方式重新执行 --run 生成新结果"
        )
        return
    if previous_digest != canonical_digest(results):
        errors.append(
            "结果文件在验证后被修改（results_sha256 不匹配），疑似手工改写状态/证据，拒绝通过"
        )


def verify_document(
    config: Mapping[str, Any],
    results: Mapping[str, Any],
    *,
    expected_commit: str,
    root: Path,
) -> tuple[list[str], dict[str, Any]]:
    """返回 (errors, 统计)。errors 为空才表示结果文件可作为 Gate 输入。"""
    errors: list[str] = []
    cases = _case_map(config)
    errors.extend(f"配置: {item}" for item in validate_config(config, root=root))

    config_baseline = str(config.get("baseline_version") or "").strip()
    results_baseline = str(results.get("baseline_version") or "").strip()
    if str(results.get("artifact_kind") or "").strip() != ARTIFACT_KIND:
        errors.append(f"artifact_kind 必须是 {ARTIFACT_KIND}")
    if str(results.get("schema_version") or "").strip() != SCHEMA_VERSION:
        errors.append(f"schema_version 必须是 {SCHEMA_VERSION}")
    if not config_baseline:
        errors.append("配置缺少 baseline_version，无法校验基线一致性")
    if not results_baseline:
        errors.append("product-results 缺少 baseline_version")
    elif config_baseline and results_baseline != config_baseline:
        errors.append(
            f"product-results baseline_version={results_baseline} 与配置 {config_baseline} 不一致"
        )

    results_environment = str(results.get("environment") or "").strip()
    config_environment = str(config.get("environment") or "").strip()
    errors.extend(f"结果环境: {item}" for item in environment_errors(results_environment))
    if results_environment and config_environment and results_environment != config_environment:
        errors.append(
            f"product-results environment={results_environment} 与配置 {config_environment} 不一致"
        )

    commit = str(results.get("commit_sha") or "").strip().lower()
    if not is_sha(commit):
        errors.append("product-results commit_sha 不是合法 40 位 SHA")
    elif commit != expected_commit:
        errors.append(
            f"product-results commit_sha={commit[:12]} 与期望 {expected_commit[:12]} 不一致"
            "（复用旧 SHA 不得作为本次证据）"
        )

    tests = results.get("tests")
    if not isinstance(tests, list) or not tests:
        errors.append("product-results 缺少 tests 记录")
        return errors, summarize([])
    ids = [str(item.get("tc_id") or "").strip() for item in tests if isinstance(item, Mapping)]
    if len(ids) != len(set(ids)):
        errors.append("product-results 存在重复 TC")
    if sorted(ids) != sorted(TC_IDS):
        errors.append(f"product-results TC 集合必须是批准的 10 条，实际 {sorted(ids)}")
    for record in tests:
        if not isinstance(record, Mapping):
            errors.append("product-results 含非对象 TC 记录")
            continue
        tc_id = str(record.get("tc_id") or "").strip()
        case = cases.get(tc_id)
        if case is None:
            errors.append(f"{tc_id}: 配置中不存在该 TC")
            continue
        record_baseline = str(record.get("baseline_version") or "").strip()
        if record_baseline and results_baseline and record_baseline != results_baseline:
            errors.append(f"{tc_id}: baseline_version={record_baseline} 与结果文件基线不一致")
        status = str(record.get("status") or "").strip().upper()
        if status == PASS and runner_argv(case.get("runner")) is None:
            errors.append(
                f"{tc_id}: 配置未注册可执行 runner，却出现 PASS；手工改写 BLOCKED→PASS 被拒绝"
            )
        errors.extend(
            record_errors(
                record,
                case=case,
                expected_commit=commit,
                expected_environment=results_environment,
                root=root,
            )
        )

    actual = summarize(tests)
    _verify_summary(results, actual, errors)
    _verify_previous_verification(results, commit, errors)
    return errors, actual


def build_verification(
    results: Mapping[str, Any],
    *,
    expected_commit: str,
    errors: list[str],
    actual: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    verified = not errors
    payload: dict[str, Any] = {
        "verified": verified,
        "verified_commit_sha": expected_commit if verified else None,
        "verified_at": iso_now(),
        "verifier": {"name": VERIFIER_NAME, "version": VERIFIER_VERSION},
        "errors": list(errors),
        "results_sha256": canonical_digest(results),
    }
    if actual is not None:
        # 结构验证通过 != 产品通过：显式写入本次 PASS 计数，避免 verified 被误读。
        payload["product_tc_pass"] = int(actual.get("product_tc_pass") or 0)
        payload["product_tc_total"] = int(actual.get("total") or 0)
    return payload


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _load_results(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("product-results 根节点必须是 JSON 对象")
    return dict(payload)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="产品 TC 结果语义验证（反伪造）")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--expected-commit", default="")
    parser.add_argument("--root", default=str(ROOT), help="artifact 路径解析根目录")
    parser.add_argument("--require-pass", action="store_true", help="任一 TC 非 PASS 即非零退出")
    parser.add_argument("--no-write", action="store_true", help="只校验，不回写 verification 块")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    results_path = Path(args.results)
    try:
        expected_commit = resolve_expected_commit(args.expected_commit)
    except ValueError as exc:
        print(f"::error::[product-verify] {exc}", file=sys.stderr)
        return 1
    try:
        config = _load_config(Path(args.config))
        results = _load_results(results_path)
    except (OSError, yaml.YAMLError, json.JSONDecodeError, ValueError) as exc:
        print(f"::error::[product-verify] 无法读取配置或结果: {exc}", file=sys.stderr)
        return 1
    errors, actual = verify_document(
        config, results, expected_commit=expected_commit, root=root
    )
    verification = build_verification(
        results, expected_commit=expected_commit, errors=errors, actual=actual
    )
    results["verification"] = verification
    if not args.no_write:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    for error in errors:
        print(f"::error::[product-verify] {error}", file=sys.stderr)
    report = {
        "verified": verification["verified"],
        "verified_commit_sha": verification["verified_commit_sha"],
        "expected_commit_sha": expected_commit,
        "environment": str(results.get("environment") or ""),
        "errors": errors,
        "status_counts": {
            key: actual.get(key, 0)
            for key in ("PASS", "FAIL", "BLOCKED", "NOT_RUN", "NOT_PROVEN", "PARTIAL", "WAIVED", "UNKNOWN")
        },
    }
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        return 1
    if args.require_pass and int(actual.get("product_tc_pass") or 0) != len(TC_IDS):
        print(
            "::error::[product-verify] --require-pass：产品 TC 未全部 PASS，"
            f"当前 {actual.get('product_tc_pass')}/{len(TC_IDS)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
