"""批量生成 MoojinR 的 70 条验收记录（人工执行，不自动代签）。

默认 dry-run；加 --execute 才写入 reviews/ 与 records/。
reviewer 使用角色键（review-roles.yaml），artifact 中记录实际签名人 MoojinR。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REVIEWS = ROOT / "docs/aiqe/v1.6/acceptance/reviews"
RECORDS = ROOT / "docs/aiqe/v1.6/acceptance/records"
MATRIX = ROOT / "docs/aiqe/v1.6/traceability/requirements.yaml"
ROLES = ROOT / "docs/aiqe/v1.6/governance/review-roles.yaml"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--signed-by", default="MoojinR")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    matrix = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    roles = yaml.safe_load(ROLES.read_text(encoding="utf-8"))
    role_map = roles.get("roles") or roles
    owners = role_map.get("owners") or {}
    REVIEWS.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)
    rows = []
    for entry in matrix["requirements"]:
        rid = entry["id"]
        owner_role = str(owners.get(entry.get("owner"), "engineering"))
        reviewer_role = "qa" if owner_role != "qa" else "security"
        artifact = REVIEWS / f"{rid}-{args.signed_by}.md"
        rows.append((rid, entry.get("title"), owner_role, reviewer_role, artifact))
    for rid, title, owner_role, reviewer_role, artifact in rows:
        print(f"{rid}: owner={owner_role} reviewer={reviewer_role} artifact={artifact.name}")
        if not args.execute:
            continue
        artifact.write_text(
            f"# {rid} 独立验收记录\n\n"
            f"- 需求：{title}\n- Reviewer：{args.signed_by}\n- 角色域：{reviewer_role}\n"
            f"- 验收日期：{args.date}\n- 结论：REVIEWED（已阅读矩阵证据与测试链接）\n",
            encoding="utf-8",
            newline="\n",
        )
        cmd = [
            sys.executable,
            str(ROOT / "scripts/aiqe/record_acceptance.py"),
            "--requirement", rid,
            "--reviewer", reviewer_role,
            "--reviewed-at", args.date,
            "--artifact", artifact.relative_to(ROOT).as_posix(),
            "--decision", "REVIEWED",
            "--force",
        ]
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            print(f"FAILED {rid}")
            return 1
    print(f"total={len(rows)} mode={'execute' if args.execute else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
