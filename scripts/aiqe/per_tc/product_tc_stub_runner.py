"""无隔离 Test 环境的占位 Runner（V1.6.2 FIX-002）。

诚实边界
--------
本 Runner **只输出 BLOCKED**，不执行任何业务动作、不生成 Run/Job ID、不输出 PASS。
它存在的唯一目的，是在没有真实隔离 Test 业务环境时让 ``run_product_tc.py --run``
仍能走通「读取配置 -> 调用已注册 runner -> 校验 runner 合同 -> 写结构化结果」的
失败闭合路径，证明框架不会把缺环境折算成通过。

真实产品 TC Runner 必须从正式入口（REST API / Worker / 外部 Runner）执行，并在
``scripts/aiqe/per_tc/runner_contract.py`` 的合同下写出 execution / assertions /
artifacts；它们不得复用本文件。

用法：
    python scripts/aiqe/per_tc/product_tc_stub_runner.py --tc TC-AIQE-001 \
        --reason "缺少隔离 Test 环境"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

AIQE_DIR = Path(__file__).resolve().parents[1]
if str(AIQE_DIR) not in sys.path:
    sys.path.insert(0, str(AIQE_DIR))

from statuses import BLOCKED  # noqa: E402
from per_tc.runner_contract import TC_IDS, non_pass_record, write_result  # noqa: E402

RUNNER_NAME = "product_tc_stub_runner"
RUNNER_VERSION = "1.0.0"
RUNNER_ENTRYPOINT = "scripts/aiqe/per_tc/product_tc_stub_runner.py"
DEFAULT_REASON = (
    "未提供隔离 Test 业务环境：占位 Runner 按 fail-closed 只输出 BLOCKED，"
    "不得作为产品 TC 验收证据"
)
DEFAULT_BLOCKED = {
    "blocked_status": BLOCKED,
    "owner": "qa-automation",
    "unblock_action": (
        "接入隔离 Test 业务环境与真实 Runner 后，由 run_product_tc.py --run 生成"
        "带 Run/Job/断言/artifact 的机器结果，再执行 --verify-results"
    ),
}


def build_blocked_record(tc_id: str, *, reason: str = "") -> dict:
    return non_pass_record(
        tc_id,
        status=BLOCKED,
        reason=reason or DEFAULT_REASON,
        runner={
            "name": RUNNER_NAME,
            "type": "external_runner",
            "version": RUNNER_VERSION,
            "entrypoint": RUNNER_ENTRYPOINT,
        },
        blocked=DEFAULT_BLOCKED,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="产品 TC 占位 Runner（只输出 BLOCKED）")
    parser.add_argument("--tc", required=True, help="TC ID，例如 TC-AIQE-001")
    parser.add_argument("--reason", default="", help="阻塞原因（默认说明缺少隔离环境）")
    parser.add_argument(
        "--result-path",
        default="",
        help="结果写出路径；缺省读取 AIQE_TC_RESULT_PATH",
    )
    args = parser.parse_args(argv)
    if args.tc not in TC_IDS:
        print(f"::error::[product-tc-stub] 未知 TC: {args.tc}", file=sys.stderr)
        return 2
    result_path = args.result_path or os.environ.get("AIQE_TC_RESULT_PATH") or ""
    if not result_path:
        print("::error::[product-tc-stub] 缺少 --result-path 或 AIQE_TC_RESULT_PATH", file=sys.stderr)
        return 1
    record = build_blocked_record(args.tc, reason=args.reason)
    write_result(result_path, record)
    print(
        json.dumps(
            {"tc_id": args.tc, "status": BLOCKED, "result": str(result_path)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
