"""V16-017 产品级 TC（TC-AIQE-001..010）执行编排。

职责
----
- ``--check-config``：校验 ``product-tc-config.yaml`` 结构（10 个 TC 齐全、runner 路径存在、
  evidence_glob 合法），不执行任何业务动作。
- ``--run``：在隔离 Test 环境按配置逐个执行 runner，强制要求：
    * 每个 runner 从正式入口（REST API / Worker / 外部 Runner）执行；
    * runner 把机器结果写到 ``AIQE_TC_RESULT_PATH``；
    * 本脚本按 ``build_evidence_index.validate_record`` 校验（PASS 必须有
      run_id/project_id/snapshot hash/job/node/assertion/artifact）；
    * 任一 TC 非 PASS → 非零退出；BLOCKED/NOT_RUN 不得计为通过。
- 没有 runner / 缺少 required_env 时输出 NOT_PROVEN 并退出 2，**不伪造结果**。

用法
----
    python scripts/aiqe/run_product_tc.py --check-config
    python scripts/aiqe/run_product_tc.py --run \
        --output docs/aiqe/v1.6/e2e/product-results.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "docs/aiqe/v1.6/e2e/product-tc-config.yaml"
DEFAULT_OUTPUT = ROOT / "docs/aiqe/v1.6/e2e/product-results.json"
TC_IDS = tuple(f"TC-AIQE-{index:03d}" for index in range(1, 11))


def _load_builder():
    path = ROOT / "scripts/aiqe/build_evidence_index.py"
    spec = importlib.util.spec_from_file_location("build_evidence_index", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = config.get("test_cases") or []
    seen = [str(case.get("tc_id")) for case in cases]
    if len(seen) != len(set(seen)):
        errors.append("test_cases 存在重复 tc_id")
    for tc_id in TC_IDS:
        if tc_id not in seen:
            errors.append(f"缺少产品 TC: {tc_id}")
    for case in cases:
        tc_id = str(case.get("tc_id") or "?")
        if not str(case.get("title") or "").strip():
            errors.append(f"{tc_id}: 缺少 title")
        if not str(case.get("spec_ref") or "").strip():
            errors.append(f"{tc_id}: 缺少 spec_ref（merged spec §20）")
        runner = case.get("runner")
        if runner is not None:
            if not isinstance(runner, list) or not runner:
                errors.append(f"{tc_id}: runner 必须是非空 list")
            else:
                script = str(runner[0])
                rest = [str(item) for item in runner[1:]]
                if Path(script).name.lower() in {"python", "python3", "python.exe"}:
                    # 解释器 + 脚本路径形式
                    if not rest:
                        errors.append(f"{tc_id}: python runner 缺少脚本路径")
                    else:
                        script = rest[0]
                        rest = rest[1:]
                if not (ROOT / script).exists():
                    errors.append(f"{tc_id}: runner 脚本不存在: {script}")
        if not str(case.get("evidence_glob") or "").strip():
            errors.append(f"{tc_id}: 缺少 evidence_glob")
        if not str(case.get("blocked_by") or "").strip() and runner is None:
            errors.append(f"{tc_id}: runner 为空时必须写 blocked_by")
    return errors


def _missing_env(config: dict[str, Any]) -> list[str]:
    required = [str(name) for name in config.get("required_env") or []]
    return [name for name in required if not os.environ.get(name)]


def _run_case(
    case: dict[str, Any], *, timeout_seconds: int = 1800
) -> dict[str, Any]:
    tc_id = str(case["tc_id"])
    runner = case.get("runner")
    if not runner:
        return {
            "tc_id": tc_id,
            "status": "NOT_RUN",
            "blocked_reason": f"未配置 runner：{case.get('blocked_by') or 'EXTERNAL'}",
        }
    with tempfile.TemporaryDirectory() as tmp:
        result_path = Path(tmp) / "result.json"
        env = dict(os.environ)
        env["AIQE_TC_RESULT_PATH"] = str(result_path)
        completed = subprocess.run(
            [str(item) for item in runner],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        if not result_path.exists():
            return {
                "tc_id": tc_id,
                "status": "FAIL",
                "blocked_reason": (
                    f"runner 未写出 {result_path.name}（exit={completed.returncode}）: "
                    f"{(completed.stderr or completed.stdout or '')[-400:]}"
                ),
            }
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        record = dict(raw or {})
        record["tc_id"] = tc_id
        try:
            validated = BUILDER.validate_record(record, index=0)
        except Exception as exc:  # noqa: BLE001 - 结果不合法即失败
            return {
                "tc_id": tc_id,
                "status": "FAIL",
                "blocked_reason": f"机器结果不合法: {exc}",
            }
        validated["runner_exit"] = completed.returncode
        return validated


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:  # pragma: no cover - 非 git 环境
        return "unknown"


def build_results(config: dict[str, Any]) -> dict[str, Any]:
    records = [_run_case(case) for case in config.get("test_cases") or []]
    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_RUN": 0}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    return {
        "schema_version": "1.0",
        "artifact_kind": "product-tc-results",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": _git_sha(),
        "environment": str(config.get("environment") or "unknown"),
        "tests": records,
        "summary": {
            **counts,
            "total": len(records),
            "product_tc_pass": counts["PASS"],
            "ga_ready": counts["PASS"] == len(TC_IDS),
        },
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="产品级 TC 执行编排")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--allow-blocked", action="store_true", help="存在 BLOCKED/NOT_RUN 时仍返回 0")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    errors = validate_config(config)
    for error in errors:
        print(f"::error::[product-tc] {error}")
    if args.check_config and not args.run:
        print(json.dumps({"ok": not errors, "cases": len(config.get("test_cases") or [])}))
        return 0 if not errors else 1
    if not args.run:
        print("::error::[product-tc] 需要 --check-config 或 --run")
        return 1
    if errors:
        return 1
    missing = _missing_env(config)
    if missing:
        payload = {
            "schema_version": "1.0",
            "artifact_kind": "product-tc-results",
            "generated_at": datetime.now(UTC).isoformat(),
            "environment": str(config.get("environment") or "unknown"),
            "status": "NOT_PROVEN",
            "reason": f"缺少必需环境变量: {missing}",
            "tests": [
                {
                    "tc_id": tc_id,
                    "status": "NOT_RUN",
                    "blocked_reason": f"缺少环境变量: {missing}",
                }
                for tc_id in TC_IDS
            ],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    results = build_results(config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(results["summary"], ensure_ascii=False))
    if results["summary"]["product_tc_pass"] == len(TC_IDS):
        return 0
    return 0 if args.allow_blocked and results["summary"]["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
