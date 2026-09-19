"""生成体育试点数据集与基线快照（Batch 261 / B4-2）。

用法（在 backend 目录下，且**必须在有资产的环境**执行）：
    python scripts/build_pilot_baseline.py --project-id 1 --environment-id 9 \
        --module-prefix 体育 --account-slot sports-tester-01 \
        --components-file fingerprint-components.json --out baseline.json

输出：数据集选择结果（接口/Web 目标与缺口）+ 环境指纹哈希 + 账号槽位**引用**。
**不含任何被测系统凭据**（09 §3.1 / H3）：-account-slot 只是槽位名，
凭据由 session_credentials_service 在运行时获取。

退出码：0 = 数据集达到试点目标（接口 50 + Web 30）；3 = 有缺口（如实报告，不凑数）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal  # noqa: E402
from app.services import pilot_dataset_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="生成试点数据集与基线快照")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--environment-id", type=int, required=True)
    parser.add_argument("--module-prefix", default="", help="只选该前缀的模块（如 体育）")
    parser.add_argument("--account-slot", default="", help="账号槽位名（不是凭据）")
    parser.add_argument("--api-limit", type=int, default=pilot_dataset_service.PILOT_API_TARGET)
    parser.add_argument("--web-limit", type=int, default=pilot_dataset_service.PILOT_WEB_TARGET)
    parser.add_argument("--components-file", default="", help="环境指纹非密因子的 JSON 文件")
    parser.add_argument("--out", default="", help="把基线写入该文件（否则只打印）")
    args = parser.parse_args()

    components: dict = {}
    if args.components_file:
        components = json.loads(Path(args.components_file).read_text(encoding="utf-8"))

    try:
        with SessionLocal() as db:
            dataset = pilot_dataset_service.select_pilot_cases(
                db,
                project_id=args.project_id,
                api_limit=args.api_limit,
                web_limit=args.web_limit,
                module_prefix=args.module_prefix,
            )
            baseline = pilot_dataset_service.build_baseline(
                db,
                project_id=args.project_id,
                environment_id=args.environment_id,
                dataset=dataset,
                account_slot=args.account_slot,
                components=components,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": "无法生成基线",
                    "hint": "确认 DATABASE_URL 指向目标环境库，且已执行 alembic upgrade head",
                    "detail": f"{type(exc).__name__}: {str(exc)[:200]}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    payload = {"dataset": dataset, "baseline": baseline}
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(serialized, encoding="utf-8")
        print(f"已写入 {args.out}")
    print(
        json.dumps(
            {
                "counts": dataset["counts"],
                "targets": dataset["targets"],
                "shortfall": dataset["shortfall"],
                "meets_target": dataset["meets_target"],
                "fingerprint_hash": baseline["environment"]["fingerprint_hash"],
                "fingerprint_confidence": baseline["environment"]["confidence"],
                "account_slot": baseline["account_slot"]["name"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if dataset["meets_target"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
