"""记录 V16-025 独立验收（人工签署）。

用法
----
    # REVIEWED：需要人工评审记录 artifact（仓库内路径）
    python scripts/aiqe/record_acceptance.py \
        --requirement V16-001-R1 \
        --reviewer qa-lead \
        --reviewed-at 2026-11-24 \
        --artifact docs/aiqe/v1.6/acceptance/reviews/V16-001-R1-qa-lead.md \
        --decision REVIEWED

    # WAIVED：需要 waiver 理由与批准人
    python scripts/aiqe/record_acceptance.py \
        --requirement TC-AIQE-010 --reviewer qa-lead --reviewed-at 2026-11-24 \
        --decision WAIVED --waiver-reason "无 30+ 标注样本，用户暂缓" --waived-by user

记录写入 ``docs/aiqe/v1.6/acceptance/records/<REQ-ID>.json``；
``check_traceability.py`` 与 ``release_verdict.py`` 会把合法记录合并进矩阵。
禁止：reviewer=pending、Owner 自审、reviewer 角色域与 owner 相同、artifact 不存在。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(SCRIPT_DIR))
from acceptance_records import (  # noqa: E402
    RECORDS_DIR,
    load_role_matrix,
    validate_record,
)

MATRIX = ROOT / "docs/aiqe/v1.6/traceability/requirements.yaml"


def _entry(requirement_id: str) -> dict | None:
    document = yaml.safe_load(MATRIX.read_text(encoding="utf-8")) or {}
    for entry in document.get("requirements") or []:
        if str(entry.get("id")) == requirement_id:
            return entry
    return None


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover - 非标准流
            pass
    parser = argparse.ArgumentParser(description="记录 AIQE V1.6 独立验收")
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--artifact", default="")
    parser.add_argument("--decision", choices=("REVIEWED", "WAIVED"), required=True)
    parser.add_argument("--waiver-reason", default="")
    parser.add_argument("--waived-by", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--records-dir", default=str(RECORDS_DIR))
    args = parser.parse_args(argv)

    entry = _entry(args.requirement)
    if entry is None:
        print(f"::error::[acceptance] 追踪矩阵中不存在需求: {args.requirement}")
        return 1
    record = {
        "requirement_id": args.requirement,
        "decision": args.decision,
        "reviewer": args.reviewer,
        "reviewed_at": args.reviewed_at,
        "artifact": args.artifact,
    }
    if args.decision == "WAIVED":
        record["waiver_reason"] = args.waiver_reason
        record["waived_by"] = args.waived_by
    errors = validate_record(
        record,
        requirement_id=args.requirement,
        owner=str(entry.get("owner") or ""),
        roles=load_role_matrix(),
    )
    if errors:
        for error in errors:
            print(f"::error::[acceptance] {error}")
        return 1
    records_dir = Path(args.records_dir)
    target = records_dir / f"{args.requirement}.json"
    if target.exists() and not args.force:
        print(f"::error::[acceptance] 记录已存在（需 --force 覆盖）: {target}")
        return 1
    records_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "written": target.relative_to(ROOT).as_posix()
                if target.is_relative_to(ROOT)
                else str(target),
                "requirement": args.requirement,
                "decision": args.decision,
                "reviewer": args.reviewer,
                "note": "请运行 check_traceability.py --strict-warnings 与 "
                "release_verdict.py --write 重算判定；记录需随 PR 提交。",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
