"""Batch 122 — 体育深度用例批量导入（编写格式 → 平台 test_case，幂等）。

将 `work-logs/evidence/batch-122/cases/**/*.json`（编写格式）展开为按入口区分的用例
写入平台 SQLite DB：
- 用户端/后台：module=`{platform}/{module}`，case_id=`SP-{入口码}-{SP- 之后部分}`
- 接口用例（域=体育-接口测试）：不展开，module/case_id 原样
- 已存在 case_id 则跳过（幂等，可重复执行）

运行: <python> scripts/sports/import-case-batch.py [--cases <dir>] [--db <sqlite路径>] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ENTRANCES = {
    "安卓iOS": "AND",
    "PC-web": "PC",
    "移动端-web": "WEB",
    "运营后台": "ADM",
    "konfi": "KON",
}
PROJECT_ID = 1


def iter_case_files(path: Path):
    if path.is_file():
        yield path
        return
    for p in sorted(path.rglob("*.json")):
        yield p


def expand(case: dict) -> list[dict]:
    """把编写格式展开为按入口的用例列表；接口用例不展开。"""
    out = []
    if case.get("domain") == "体育-接口测试":
        item = dict(case)
        item["_platform"] = "接口"
        out.append(item)
        return out
    platforms = case.get("platforms") or []
    module = str(case.get("module", "")).strip("/")
    base = case.get("case_id", "")
    for pf in platforms:
        code = ENTRANCES.get(pf)
        if not code:
            continue
        item = dict(case)
        item["module"] = f"{pf}/{module}"
        if base.startswith("SP-"):
            item["case_id"] = f"SP-{code}-{base[3:]}"
        item["_platform"] = pf
        out.append(item)
    return out


def _ser(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(Path(__file__).resolve().parents[1] / "work-logs" / "evidence" / "batch-122" / "cases"))
    ap.add_argument("--db", default=str(Path(__file__).resolve().parents[1] / "backend" / "data" / "platform-sports-case-quality.db"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.cases)
    if not root.exists():
        print(f"[importer] cases 目录不存在: {root}", flush=True)
        return 1

    expanded: list[dict] = []
    for fp in iter_case_files(root):
        data = json.loads(fp.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [data]
        for case in items:
            expanded.extend(expand(case))
    print(f"[importer] 展开后共 {len(expanded)} 条", flush=True)

    if args.dry_run:
        return 0

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute("SELECT case_id FROM test_case WHERE case_id LIKE 'SP-%'")
    existing = {r[0] for r in cur.fetchall()}

    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    inserted = skipped = 0
    for c in expanded:
        cid = c["case_id"]
        if cid in existing:
            skipped += 1
            continue
        tags = list(c.get("tags") or [])
        tags.append("功能用例" if c.get("case_type") != "api" else "接口用例")
        tags.append(c["_platform"])
        cur.execute(
            """INSERT INTO test_case
               (project_id, case_id, title, domain, module, case_type, priority, status, tags,
                preconditions, steps, expected_result, api_method, api_endpoint, api_spec_ref,
                api_headers, api_body, api_assertions, review_comment, source, review_status,
                reviewer_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                PROJECT_ID, cid, c["title"], c.get("domain", ""), c["module"],
                c.get("case_type", "manual"), c.get("priority", "P1"), "active",
                json.dumps(tags, ensure_ascii=False),
                c.get("preconditions", ""),
                json.dumps(c.get("steps") or [], ensure_ascii=False),
                c.get("expected_result", ""),
                c.get("api_method", ""), c.get("api_endpoint", ""), "",
                "", _ser(c.get("api_body")), _ser(c.get("api_assertions")), "",
                "batch-122", "draft", 0, now, now,
            ),
        )
        existing.add(cid)
        inserted += 1
    con.commit()
    cur.execute("SELECT COUNT(*) FROM test_case WHERE case_id LIKE 'SP-%'")
    total_sp = cur.fetchone()[0]
    print(f"[importer] inserted={inserted} skipped(existing)={skipped} SP-用例总数={total_sp}", flush=True)
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
